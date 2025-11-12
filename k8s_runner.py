"""Run the AI coding container on Kubernetes with a docker-like CLI."""

from __future__ import annotations

import argparse
import re
import sys
import time
import uuid
from typing import Dict, Iterable, List, Optional

from kubernetes import client, config, watch
from kubernetes.client import ApiException
from kubernetes.config.config_exception import ConfigException


class K8sJobRunnerError(RuntimeError):
    """Raised when the Kubernetes job runner encounters a fatal error."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the AI Coding container on Kubernetes in a docker-like fashion.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("image", help="Container image reference to run.")
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command (and arguments) to execute inside the container. Prefix with -- to separate from runner flags.",
    )

    parser.add_argument("--namespace", default="default", help="Target Kubernetes namespace.")
    parser.add_argument("--name", help="Optional base name for the Job/Pod. A unique suffix is automatically added.")
    parser.add_argument("--container-name", default="ai-coder", help="Container name inside the Pod.")
    parser.add_argument(
        "--entrypoint",
        nargs="+",
        help="Override the container entrypoint (equivalent to Docker --entrypoint).",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        help="Environment variable in KEY=VALUE form. Repeatable.",
    )
    parser.add_argument(
        "--label",
        action="append",
        default=[],
        help="Additional label in key=value form applied to Job and Pod. Repeatable.",
    )
    parser.add_argument(
        "--annotation",
        action="append",
        default=[],
        help="Annotation in key=value form applied to the Pod template. Repeatable.",
    )
    parser.add_argument(
        "--image-pull-secret",
        dest="image_pull_secrets",
        action="append",
        default=[],
        help="Name of an imagePullSecret to attach. Repeatable.",
    )
    parser.add_argument("--service-account", help="Service account to use for the Pod.")
    parser.add_argument(
        "--request-cpu",
        help="CPU request for the container (e.g. 500m).",
    )
    parser.add_argument(
        "--request-memory",
        help="Memory request for the container (e.g. 1Gi).",
    )
    parser.add_argument("--limit-cpu", help="CPU limit for the container (e.g. 1).")
    parser.add_argument("--limit-memory", help="Memory limit for the container (e.g. 2Gi).")
    parser.add_argument(
        "--workspace-mount",
        default="/workspace",
        help="Mount path for an ephemeral emptyDir workspace.",
    )
    parser.add_argument(
        "--no-workspace",
        action="store_true",
        help="Disable creation of the ephemeral workspace volume.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Maximum time in seconds to wait for Job completion.",
    )
    parser.add_argument(
        "--context",
        help="Kubeconfig context to use. Falls back to in-cluster configuration if not available.",
    )
    parser.add_argument(
        "--backoff-limit",
        type=int,
        default=0,
        help="Number of retries before the Job is considered failed.",
    )
    parser.add_argument(
        "--restart-policy",
        choices=["Never", "OnFailure"],
        default="Never",
        help="Pod restart policy.",
    )
    parser.add_argument(
        "--image-pull-policy",
        choices=["Always", "IfNotPresent", "Never"],
        default="IfNotPresent",
        help="Container image pull policy.",
    )

    cleanup_group = parser.add_mutually_exclusive_group()
    cleanup_group.add_argument(
        "--auto-clean",
        dest="auto_clean",
        action="store_true",
        help="Automatically delete the Job and Pods when execution finishes.",
    )
    cleanup_group.add_argument(
        "--keep",
        dest="auto_clean",
        action="store_false",
        help="Keep the created Job and Pods after completion.",
    )
    parser.set_defaults(auto_clean=True)

    return parser


def _parse_key_value_pairs(pairs: Iterable[str], flag_name: str) -> Dict[str, str]:
    parsed: Dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise K8sJobRunnerError(f"{flag_name} values must be in key=value format: '{item}'")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise K8sJobRunnerError(f"{flag_name} entries require a non-empty key: '{item}'")
        parsed[key] = value
    return parsed


def _parse_env_vars(values: Iterable[str]) -> List[client.V1EnvVar]:
    env_kv = _parse_key_value_pairs(values, "--env")
    return [client.V1EnvVar(name=name, value=value) for name, value in env_kv.items()]


def _sanitize_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "ai-coder"


def _generate_job_name(base_name: Optional[str]) -> str:
    base = _sanitize_name(base_name or "ai-coder-run")
    suffix = uuid.uuid4().hex[:6]
    max_prefix_length = max(1, 63 - len(suffix) - 1)
    prefix = base[:max_prefix_length].rstrip("-")
    if not prefix:
        prefix = "ai-coder"[:max_prefix_length]
    job_name = f"{prefix}-{suffix}"
    job_name = re.sub(r"-+", "-", job_name).strip("-")
    return job_name[:63]


def _load_kube_configuration(context: Optional[str]) -> None:
    try:
        config.load_kube_config(context=context)
        return
    except ConfigException:
        pass

    try:
        config.load_incluster_config()
    except ConfigException as exc:  # pragma: no cover - depends on runtime environment
        raise K8sJobRunnerError(
            "Unable to load Kubernetes configuration. Provide a kubeconfig or run inside a cluster."
        ) from exc


def _build_resource_requirements(args: argparse.Namespace) -> Optional[client.V1ResourceRequirements]:
    requests: Dict[str, str] = {}
    limits: Dict[str, str] = {}

    if args.request_cpu:
        requests["cpu"] = args.request_cpu
    if args.request_memory:
        requests["memory"] = args.request_memory
    if args.limit_cpu:
        limits["cpu"] = args.limit_cpu
    if args.limit_memory:
        limits["memory"] = args.limit_memory

    if not requests and not limits:
        return None

    return client.V1ResourceRequirements(
        requests=requests or None,
        limits=limits or None,
    )


def _build_job_definition(
    args: argparse.Namespace,
    job_name: str,
    labels: Dict[str, str],
    annotations: Dict[str, str],
    env_vars: List[client.V1EnvVar],
) -> client.V1Job:
    container = client.V1Container(
        name=args.container_name,
        image=args.image,
        image_pull_policy=args.image_pull_policy,
        env=env_vars or None,
        command=args.entrypoint or None,
        args=args.command or None,
        resources=_build_resource_requirements(args),
    )

    volumes: List[client.V1Volume] = []
    volume_mounts: List[client.V1VolumeMount] = []
    if not args.no_workspace:
        volume = client.V1Volume(
            name="workspace",
            empty_dir=client.V1EmptyDirVolumeSource(),
        )
        mount = client.V1VolumeMount(
            name="workspace",
            mount_path=args.workspace_mount,
        )
        volumes.append(volume)
        volume_mounts.append(mount)
        container.volume_mounts = volume_mounts

    pod_labels = {"app": "ai-coder", **labels}
    pod_annotations = annotations or None

    pod_spec = client.V1PodSpec(
        restart_policy=args.restart_policy,
        containers=[container],
        service_account_name=args.service_account,
        volumes=volumes or None,
        image_pull_secrets=[client.V1LocalObjectReference(name=name) for name in args.image_pull_secrets]
        or None,
    )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels=pod_labels, annotations=pod_annotations),
        spec=pod_spec,
    )

    job_spec = client.V1JobSpec(
        template=template,
        backoff_limit=args.backoff_limit,
    )

    metadata = client.V1ObjectMeta(name=job_name, labels=pod_labels)

    return client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=metadata,
        spec=job_spec,
    )


def _wait_for_pod(
    api: client.CoreV1Api,
    namespace: str,
    job_name: str,
    timeout: int,
) -> client.V1Pod:
    label_selector = f"job-name={job_name}"
    deadline = time.time() + timeout
    last_error: Optional[str] = None

    while time.time() < deadline:
        pod_list = api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
        if pod_list.items:
            pod = pod_list.items[0]
            phase = pod.status.phase or ""
            if phase in {"Running", "Succeeded", "Failed"}:
                return pod

            waiting_reasons = []
            for status in pod.status.container_statuses or []:
                if status.state and status.state.waiting:
                    waiting_reasons.append(status.state.waiting.reason or "")
                    if status.state.waiting.message:
                        last_error = status.state.waiting.message

            if waiting_reasons:
                blocked = {"ErrImagePull", "ImagePullBackOff", "CreateContainerConfigError"}
                if any(reason in blocked for reason in waiting_reasons):
                    message = last_error or ", ".join(sorted(set(waiting_reasons)))
                    raise K8sJobRunnerError(
                        f"Pod {pod.metadata.name} is stuck waiting: {message}"
                    )
        time.sleep(1)

    raise TimeoutError(
        f"Timed out waiting for a pod from job '{job_name}' to become ready (timeout={timeout}s)."
    )


def _stream_pod_logs(
    api: client.CoreV1Api,
    namespace: str,
    pod_name: str,
    container_name: str,
) -> None:
    log_watch = watch.Watch()
    try:
        for chunk in log_watch.stream(
            api.read_namespaced_pod_log,
            name=pod_name,
            namespace=namespace,
            container=container_name,
            follow=True,
            _preload_content=False,
        ):
            if isinstance(chunk, bytes):
                decoded = chunk.decode("utf-8", errors="replace")
            else:
                decoded = str(chunk)
            sys.stdout.write(decoded)
            sys.stdout.flush()
    except ApiException as exc:
        if exc.status not in {0, 200}:
            raise
    finally:
        log_watch.stop()


def _wait_for_job_completion(
    api: client.BatchV1Api,
    namespace: str,
    job_name: str,
    timeout: int,
) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = api.read_namespaced_job_status(name=job_name, namespace=namespace)
        status = job.status
        if status.succeeded and status.succeeded > 0:
            return "succeeded"
        if status.failed and status.failed > 0:
            return "failed"
        if status.conditions:
            for condition in status.conditions:
                if condition.status == "True" and condition.type in {"Failed", "Complete"}:
                    return condition.type.lower()
        time.sleep(2)
    raise TimeoutError(
        f"Job '{job_name}' did not complete within the timeout window ({timeout}s)."
    )


def _cleanup_job(api: client.BatchV1Api, namespace: str, job_name: str) -> None:
    delete_opts = client.V1DeleteOptions(propagation_policy="Foreground")
    try:
        api.delete_namespaced_job(
            name=job_name,
            namespace=namespace,
            body=delete_opts,
        )
    except ApiException as exc:
        if exc.status != 404:
            raise


def main() -> None:  # noqa: C901 - high-level orchestration with branching
    parser = _build_parser()
    args = parser.parse_args()

    if args.command and args.command[0] == "--":
        args.command = args.command[1:]

    try:
        env_vars = _parse_env_vars(args.env)
        labels = _parse_key_value_pairs(args.label, "--label")
        annotations = _parse_key_value_pairs(args.annotation, "--annotation")
    except K8sJobRunnerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        _load_kube_configuration(args.context)
    except K8sJobRunnerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    batch_api = client.BatchV1Api()
    core_api = client.CoreV1Api()

    job_name = _generate_job_name(args.name)
    exit_code = 1
    job_created = False

    try:
        job_definition = _build_job_definition(args, job_name, labels, annotations, env_vars)
        batch_api.create_namespaced_job(namespace=args.namespace, body=job_definition)
        job_created = True
        print(f"Job '{job_name}' created in namespace '{args.namespace}'.")

        pod = _wait_for_pod(core_api, args.namespace, job_name, args.timeout)
        print(f"Streaming logs from pod '{pod.metadata.name}'...", flush=True)
        _stream_pod_logs(core_api, args.namespace, pod.metadata.name, args.container_name)

        status = _wait_for_job_completion(batch_api, args.namespace, job_name, args.timeout)
        if status in {"succeeded", "complete"}:
            print("Job completed successfully.")
            exit_code = 0
        else:
            print(f"Job finished with status: {status}", file=sys.stderr)
            exit_code = 1

    except TimeoutError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        exit_code = 1
    except K8sJobRunnerError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        exit_code = 1
    except ApiException as exc:
        print(f"Kubernetes API error: {exc}", file=sys.stderr)
        exit_code = 1
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.", file=sys.stderr)
        exit_code = 130
    finally:
        if job_created and args.auto_clean:
            try:
                _cleanup_job(batch_api, args.namespace, job_name)
                print(f"Cleaned up job '{job_name}'.")
            except ApiException as exc:
                print(f"Warning: failed to clean up job '{job_name}': {exc}", file=sys.stderr)
        elif job_created:
            print(
                "Job resources retained. Manually delete with: "
                f"kubectl delete job {job_name} -n {args.namespace}"
            )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

import typing


class Constants:
    SEPARATOR: typing.ClassVar = "\x1f"
    TOP_KEYS: typing.ClassVar = [
        "schema_version",
        "dataset_version",
        "timestamp",
        "source",
        "license",
        "doi",
        "nodes",
        "edges",
    ]
    SOURCE_KEYS: typing.ClassVar = ["repo", "commit"]
    NODE_KEYS: typing.ClassVar = [
        "id",
        "kind",
        "language",
        "stack",
        "broker",
        "native_kind",
        "native_name",
        "routing",
        "delivery",
    ]
    EDGE_KEYS: typing.ClassVar = [
        "id",
        "caller",
        "caller_endpoint",
        "callee",
        "callee_endpoint",
        "type",
        "pattern",
        "routing_key",
        "headers",
        "selector",
        "role",
        "derived_from",
        "static",
        "observed",
    ]

    RELEASE_ONLY: typing.ClassVar = ["dataset_version", "timestamp", "source", "doi"]

    KINDS: typing.ClassVar = {
        "service",
        "datastore",
        "destination",
        "external",
        "client",
        "broker",
    }
    LANGUAGES: typing.ClassVar = {"go", "java", "python"}
    NATIVE_KINDS: typing.ClassVar = {
        "exchange",
        "queue",
        "topic",
        "subject",
        "subscription",
        "consumer-group",
        "stream",
    }
    ROUTINGS: typing.ClassVar = {
        "exact",
        "pattern",
        "broadcast",
        "headers",
        "hash",
        "none",
    }
    DELIVERIES: typing.ClassVar = {"competing", "broadcast"}
    TYPES: typing.ClassVar = {
        "rest",
        "grpc",
        "grpc-stream",
        "websocket",
        "async",
        "async-derived",
        "query",
    }
    ROLES: typing.ClassVar = {"primary", "alternate", "dead-letter"}
    PATTERNS: typing.ClassVar = {
        "literal-url",
        "string-concatenation",
        "env-var-config",
        "cross-file-constant",
        "class-field-default",
        "client-wrapper",
        "conditional-branch",
        "closure-captured",
        "gateway-indirection",
        "service-discovery-lookup",
    }
    PATTERN_TYPES: typing.ClassVar = {"rest", "grpc", "grpc-stream"}

# Infrastructure

The root `docker-compose.yml` contains the local PostgreSQL, Qdrant, backend and
frontend services. Production overlays (managed database, private Qdrant,
secrets manager, TLS ingress and observability) belong in this directory.


# CSE160 OpenCL Docker

To run locally

```bash
python3 -m opencl_docker --image <base image> --tag <release tag> --pocl_version v<version> --output Dockerfile && docker build . -t <image name>:<tag>
```
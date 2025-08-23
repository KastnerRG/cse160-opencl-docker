from opencl_docker.dockerfile import Dockerfile
from argparse import ArgumentParser
import platform
from typing import Any

def update_packages(dockerfile: Dockerfile):
    dockerfile.run("apt-get update && apt-get upgrade -y && \
                    apt-get clean && rm -rf /var/lib/apt/lists/*")
    
def install_intel_opencl(dockerfile: Dockerfile):
    if platform.processor() == "x86_64":
        dockerfile.run('apt-get update && apt-get -y install wget gnupg2 && \
                        wget -O- https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB \
                        | gpg --dearmor | tee /usr/share/keyrings/oneapi-archive-keyring.gpg && \
                        echo "deb [signed-by=/usr/share/keyrings/oneapi-archive-keyring.gpg] https://apt.repos.intel.com/oneapi all main"  | tee /etc/apt/sources.list.d/oneAPI.list && \
                        apt-get update && apt-get install -y  intel-oneapi-runtime-libs && \
                        apt-get clean && rm -rf /var/lib/apt/lists/*')
        
def install_dependencies(dockerfile: Dockerfile, args: Any):
    dependencies = ["build-essential",
                    "git",
                    "llvm",
                    "libclang-cpp-dev",
                    "llvm-dev",
                    "clang",
                    "libclang-dev",
                    "cmake",
                    "pkg-config",
                    "make",
                    "ninja-build",
                    "libhwloc-dev",
                    "clinfo",
                    "dialog",
                    "apt-utils",
                    "libxml2-dev",
                    "vim",
                    "gdb",
                    "valgrind",
                    "libclblast-dev"]
    
    if "qualcomm" in args.image:
        dependencies.extend([
            "qcom-adreno-cl-dev"
        ])
    else:
        dependencies.extend([
            "opencl-headers",
            "ocl-icd-libopencl1",
            "ocl-icd-dev",
            "ocl-icd-opencl-dev"])

    dockerfile.run(f"apt-get update && apt-get install -y {" ".join(dependencies)} \
                    && apt-get clean && rm -rf /var/lib/apt/lists/*")
    
def install_pocl(dockerfile: Dockerfile, args: Any):
    # We'll install PoCL on everything.
    # Intel OpenCL driver doesn't support aarch64
    # PoCL has CUDA OpenCL support
    dockerfile.run("git clone https://github.com/pocl/pocl.git /pocl")
    dockerfile.workdir("/pocl")
    dockerfile.run("git checkout v7.0 && mkdir build")
    dockerfile.workdir("/pocl/build")

    cuda_switch = ""
    if "nvidia" in args.image:
        cuda_switch = "-DENABLE_CUDA=ON"

    dockerfile.run(f"cmake -DCMAKE_BUILD_TYPE=Release -DENABLE_VALGRIND=ON -DCMAKE_INSTALL_PREFIX=/ {cuda_switch} .. && \
                     make -j && \
                     make install && \
                     rm -rf /pocl")
    
def install_opencl_intercept_layer(dockerfile: Dockerfile):
    dockerfile.run("git clone https://github.com/intel/opencl-intercept-layer.git /opencl-intercept-layer")
    dockerfile.workdir("/opencl-intercept-layer")
    dockerfile.run("git checkout v3.0.5 && mkdir build")
    dockerfile.workdir("/opencl-intercept-layer/build")
    dockerfile.run("cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/ocl-intercept .. && \
                    make -j && \
                    make install && \
                    rm -rf /opencl-intercept-layer && \
                    ln -s /ocl-intercept/bin/cliloader /bin/cliloader")

def configure_user(dockerfile: Dockerfile):
    dockerfile.user("ubuntu")
    dockerfile.env(HOME="/home/ubuntu")
    dockerfile.run("mkdir -p ${HOME}")
    dockerfile.workdir("${HOME}")

def main():
    parser = ArgumentParser("opencl-docker")
    parser.add_argument("-i", "--image", required=True, help="The image for the resulting Dockerfile.")
    parser.add_argument("-o", "--output", required=True, help="The output file for the Dockerfile.")

    args = parser.parse_args()

    dockerfile = Dockerfile(args.image)

    install_intel_opencl(dockerfile)
    update_packages(dockerfile)
    install_dependencies(dockerfile, args)
    install_pocl(dockerfile, args)
    install_opencl_intercept_layer(dockerfile)

    configure_user(dockerfile)
    
    dockerfile.cmd("/bin/bash")

    with open(args.output, "w") as f:
        f.write(str(dockerfile))

if __name__ == "__main__":
    main()
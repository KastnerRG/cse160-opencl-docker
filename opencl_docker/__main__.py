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
                    "llvm-20",
                    "llvm-20-dev",
                    "clang-20",
                    "libclang-20-dev",
                    "libclang-cpp20-dev",
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
                    "oclgrind",
                    "python3-numpy",
                    "netcat-openbsd"
                ]
    
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

    # Ubuntu 22.04 needs ocl-icd from this PPA in order to support newer versions of POCL
    if "22.04" in args.image:
        dockerfile.run(f'apt-get update && apt-get -y install software-properties-common && \
                        add-apt-repository ppa:ocl-icd/ppa && apt-get update && \
                         apt-get install -y ocl-icd-libopencl1 ocl-icd-opencl-dev')
        ubuntu_name = "jammy"
    else: #22.04
        ubuntu_name = "noble"
    dockerfile.run(f'apt-get update && apt-get -y install wget gnupg2 && \
                    echo "deb http://apt.llvm.org/{ubuntu_name}/ llvm-toolchain-{ubuntu_name}-20 main" | tee /etc/apt/sources.list.d/llvm-toolchain-{ubuntu_name}.list && \
                    wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add - && \
                    apt-get update && apt-get install -y {" ".join(dependencies)} \
                    && apt-get clean && rm -rf /var/lib/apt/lists/*')
    
def install_pocl(dockerfile: Dockerfile, args: Any):
    # We'll install PoCL on everything.
    # Intel OpenCL driver doesn't support aarch64
    # PoCL has CUDA OpenCL support
    dockerfile.run("git clone https://github.com/pocl/pocl.git /pocl")
    dockerfile.workdir("/pocl")
    dockerfile.run(f"git checkout {args.pocl_version} && mkdir build")
    dockerfile.workdir("/pocl/build")

    cuda_switch = ""
    if "nvidia" in args.image:
        cuda_switch = "-DENABLE_CUDA=ON"

    dockerfile.run(f"cmake -DCMAKE_BUILD_TYPE=Release -DENABLE_VALGRIND=ON -DCMAKE_INSTALL_PREFIX=/ {cuda_switch} .. && \
                     make -j && \
                     make install && \
                     rm -rf /pocl")
    
def install_cuda_dsmlp(dockerfile: Dockerfile, args: Any):
    # Hack to port old cuda version forward.
    # The DSMLP has old drivers for the 1080Ti and there is
    # a possible compat issue with newer POCL versions.
    # These commands are only good enough for another CUDA 12 base image
    if "dsmlp" in args.tag:
        dockerfile.copy("--from=nvcr.io/nvidia/cuda:12.2.0-devel-ubuntu22.04 /usr/local/cuda-12.2", "/usr/local/cuda-12.2", src_img="nvcr.io/nvidia/cuda:12.2.0-devel-ubuntu22.04")
        dockerfile.run("rm /usr/local/cuda /usr/local/cuda-12; ln -sf cuda-12.2 /usr/local/cuda && ln -sf cuda-12.2 /usr/local/cuda-12")
        dockerfile.env(**{
            'CUDA_HOME' : "/usr/local/cuda",
            'PATH' : '${CUDA_HOME}/bin:${PATH}'
        })

    
def install_cuda_drivers(dockerfile: Dockerfile, args: Any):
    if "nvidia" in args.image:
        dockerfile.run('mkdir -p /etc/OpenCL/vendors && \
                        echo "libnvidia-opencl.so.1" > /etc/OpenCL/vendors/nvidia.icd')
        dockerfile.env(**{
            "NVIDIA_VISIBLE_DEVICES": "all",
            "NVIDIA_DRIVER_CAPABILITIES": "compute,utility"
        })
    
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
    
def install_cl_blast(dockerfile: Dockerfile):
    dockerfile.run("git clone https://github.com/CNugteren/CLBlast.git /clblast")
    dockerfile.workdir("/clblast")
    dockerfile.run("git checkout 1.6.3 && mkdir build")
    dockerfile.workdir("/clblast/build")

    dockerfile.run(f"cmake -DCMAKE_BUILD_TYPE=Release .. && \
                    make -j && \
                    make install && \
                    rm -rf /clblast")

def configure_user(dockerfile: Dockerfile):
    dockerfile.user("ubuntu")
    dockerfile.env(HOME="/home/ubuntu")
    dockerfile.run("mkdir -p ${HOME} && \
                    cp -r /etc/skel/. ${HOME} && \
                    chown -R ubuntu:ubuntu ${HOME} && \
                    echo 'export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH' >> ${HOME}/.bashrc")
    dockerfile.workdir("${HOME}")

def main():
    parser = ArgumentParser("opencl-docker")
    parser.add_argument("-i", "--image", required=True, help="The image for the resulting Dockerfile.")
    parser.add_argument("-o", "--output", required=True, help="The output file for the Dockerfile.")
    parser.add_argument("-t", "--tag", required=True, help="The push tag for the Dockerfile.")
    parser.add_argument("-p", "--pocl_version", required=True, help="The version of pocl to install.")

    args = parser.parse_args()

    dockerfile = Dockerfile(args.image)

    install_intel_opencl(dockerfile)
    update_packages(dockerfile)
    install_dependencies(dockerfile, args)
    install_pocl(dockerfile, args)
    # install_cuda_drivers(dockerfile, args)
    install_opencl_intercept_layer(dockerfile)
    install_cl_blast(dockerfile)
    install_cuda_dsmlp(dockerfile, args)

    configure_user(dockerfile)
    
    dockerfile.cmd("/bin/bash")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(str(dockerfile))

if __name__ == "__main__":
    main()

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
                ]
    
    if "qualcomm" in args.image:
        dependencies.extend([
            "qcom-adreno-cl-dev"
        ])
    elif "rocm" in args.image:
        dependencies.extend([
            "rocm-opencl-runtime",
            "rocm-opencl-dev"
        ])
    else:
        dependencies.extend([
            "opencl-headers",
            "ocl-icd-libopencl1",
            "ocl-icd-dev",
            "ocl-icd-opencl-dev"])

    if "22.04" in args.image:
        dockerfile.run(f'apt-get update && apt-get -y install wget gnupg2 && \
                        echo "deb http://apt.llvm.org/jammy/ llvm-toolchain-jammy-20 main" | tee /etc/apt/sources.list.d/llvm-toolchain-jammy.list && \
                        wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add - && \
                        apt-get update && apt-get install -y {" ".join(dependencies)} \
                        && apt-get clean && rm -rf /var/lib/apt/lists/*')
    else:
        dockerfile.run(f'apt-get update && apt-get -y install wget gnupg2 && \
                        echo "deb http://apt.llvm.org/noble/ llvm-toolchain-noble-20 main" | tee /etc/apt/sources.list.d/llvm-toolchain-noble.list && \
                        wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add - && \
                        apt-get update && apt-get install -y {" ".join(dependencies)} \
                        && apt-get clean && rm -rf /var/lib/apt/lists/*')
    
def install_pocl(dockerfile: Dockerfile, args: Any):
    # We'll install PoCL on everything.
    # Intel OpenCL driver doesn't support aarch64
    # PoCL has CUDA OpenCL support
    if "rocm" not in args.image:
        dockerfile.run("git clone https://github.com/pocl/pocl.git /pocl")
        dockerfile.workdir("/pocl")
        dockerfile.run("git checkout v7.1 && mkdir build")
        dockerfile.workdir("/pocl/build")

        cuda_switch = ""
        if "nvidia" in args.image:
            cuda_switch = "-DENABLE_CUDA=ON"

        dockerfile.run(f"cmake -DCMAKE_BUILD_TYPE=Release -DENABLE_VALGRIND=ON -DCMAKE_INSTALL_PREFIX=/ {cuda_switch} .. && \
                         make -j && \
                         make install && \
                         rm -rf /pocl")
    
def install_cuda_drivers(dockerfile: Dockerfile, args: Any):
    if "nvidia" in args.image:
        dockerfile.run('mkdir -p /etc/OpenCL/vendors && \
                        echo "libnvidia-opencl.so.1" > /etc/OpenCL/vendors/nvidia.icd')
        dockerfile.env(**{
            "NVIDIA_VISIBLE_DEVICES": "all",
            "NVIDIA_DRIVER_CAPABILITIES": "compute,utility"
        })

def install_rocm_drivers(dockerfile: Dockerfile, args: Any):
    if "rocm" in args.image:
        dockerfile.env(**{
            "ROCR_VISIBLE_DEVICES": "all",
            #"HIP_VISIBLE_DEVICES": "all"
        })
    if platform.system() == "Windows":
        dockerfile.run("apt-get update && \
                       wget https://repo.radeon.com/amdgpu-install/7.1.1/ubuntu/noble/amdgpu-install_7.1.1.70101-1_all.deb && \
                       yes Y | apt-get install -y ./amdgpu-install_7.1.1.70101-1_all.deb")
        dockerfile.run("yes Y | amdgpu-install --uninstall")
        dockerfile.run("apt-get remove -y ./amdgpu-install_7.1.1.70101-1_all.deb")
        dockerfile.run("apt-get update && apt autoremove -y &&\
                       wget https://repo.radeon.com/amdgpu-install/6.4.2.1/ubuntu/noble/amdgpu-install_6.4.60402-1_all.deb && \
                       yes Y | apt-get install -y ./amdgpu-install_6.4.60402-1_all.deb --allow-downgrades")
        #dockerfile.run("amdgpu-install -y --usecase=wsl,rocm,opencl --no-dkms")
        dockerfile.run("amdgpu-install -y --usecase=wsl,rocm,opencl")
        dockerfile.run("apt-get install -y rocm-opencl-runtime rocm-opencl-dev amd-container-toolkit ocl-icd-opencl-dev opencl-headers clinfo")
    
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

def configure_user(dockerfile: Dockerfile, args: Any):
    dockerfile.user("ubuntu")
    dockerfile.env(HOME="/home/ubuntu")
    dockerfile.run("mkdir -p ${HOME} && \
                    cp -r /etc/skel/. ${HOME} && \
                    chown -R ubuntu:ubuntu ${HOME} && \
                    echo 'export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH' >> ${HOME}/.bashrc")
    dockerfile.workdir("${HOME}")
    if "rocm" in args.image:
        dockerfile.user("root")
        # Device Specific
        # dockerfile.run("groupmod -g 105 render")
        # dockerfile.run("groupmod -g 39 video")
        dockerfile.run("usermod -a -G render,video,irc ubuntu")
        dockerfile.user("ubuntu")

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
    # install_cuda_drivers(dockerfile, args)
    install_rocm_drivers(dockerfile, args)
    install_opencl_intercept_layer(dockerfile)
    install_cl_blast(dockerfile)

    configure_user(dockerfile, args)
    
    dockerfile.cmd("/bin/bash")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(str(dockerfile))

if __name__ == "__main__":
    main()

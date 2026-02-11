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
                    "python3-numpy"
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
    
    if "dsmlp" in args.tag:
        dependencies.extend([
            "openssh-server",
            "netcat-openbsd"
        ])

    if "pytorch" in args.tag:
        dependencies.extend([
            "python3-dev"
        ])

    # Ubuntu 22.04 needs ocl-icd from this PPA in order to support newer versions of POCL
    if "22.04" in args.image:
        dockerfile.run(f'apt-get update && apt-get -y install software-properties-common && \
                         add-apt-repository ppa:ocl-icd/ppa && apt-get update && \
                         apt-get install -y ocl-icd-libopencl1 ocl-icd-opencl-dev')
        ubuntu_name = "jammy"
    else: # 24.04
        ubuntu_name = "noble"

    dockerfile.run(f'apt-get update && apt-get -y install wget gnupg2 && \
                    echo "deb http://apt.llvm.org/{ubuntu_name}/ llvm-toolchain-{ubuntu_name}-20 main" | tee /etc/apt/sources.list.d/llvm-toolchain-{ubuntu_name}.list && \
                    wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add - && \
                    apt-get update && apt-get install -y {" ".join(dependencies)} \
                    && apt-get clean && rm -rf /var/lib/apt/lists/*')
    
def install_pocl(dockerfile: Dockerfile, args: Any):
    # Intel OpenCL driver doesn't support aarch64
    # PoCL has CUDA OpenCL support
    dockerfile.run("git clone https://github.com/pocl/pocl.git /pocl")
    dockerfile.workdir("/pocl")
    dockerfile.run(f"git checkout {args.pocl_version} && mkdir build")
    dockerfile.workdir("/pocl/build")

    pocl_switches = ""
    if "nvidia" in args.image:
        pocl_switches += "-DENABLE_CUDA=ON "

    if platform.processor() == "arm":
        pocl_switches += "-DLLC_HOST_CPU=general "

    dockerfile.run(f"cmake -DCMAKE_BUILD_TYPE=Release -DENABLE_VALGRIND=ON -DCMAKE_INSTALL_PREFIX=/ {pocl_switches} .. && \
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
            'CUDA_VERSION' : "12.2.0",
            'NVIDIA_REQUIRE_CUDA': 'cuda>=12.2 brand=tesla,driver>=470,driver<471 brand=unknown,driver>=470,driver<471 brand=nvidia,driver>=470,driver<471 brand=nvidiartx,driver>=470,driver<471 brand=geforce,driver>=470,driver<471 brand=geforcertx,driver>=470,driver<471 brand=quadro,driver>=470,driver<471 brand=quadrortx,driver>=470,driver<471 brand=titan,driver>=470,driver<471 brand=titanrtx,driver>=470,driver<471 brand=tesla,driver>=525,driver<526 brand=unknown,driver>=525,driver<526 brand=nvidia,driver>=525,driver<526 brand=nvidiartx,driver>=525,driver<526 brand=geforce,driver>=525,driver<526 brand=geforcertx,driver>=525,driver<526 brand=quadro,driver>=525,driver<526 brand=quadrortx,driver>=525,driver<526 brand=titan,driver>=525,driver<526 brand=titanrtx,driver>=525,driver<526',
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

def install_intelGPU_drivers(dockerfile: Dockerfile, args: Any):
    if "intel" in args.tag:
        if "22.04" in args.image:
            dockerfile.run('apt-get install -y gpg-agent wget')
            dockerfile.run('wget -qO - https://repositories.intel.com/graphics/intel-graphics.key |\
                            gpg --dearmor --output /usr/share/keyrings/intel-graphics.gpg')
            dockerfile.run("echo 'deb [arch=amd64,i386 signed-by=/usr/share/keyrings/intel-graphics.gpg]\
                            https://repositories.intel.com/graphics/ubuntu jammy arc' | \
                            tee  /etc/apt/sources.list.d/intel.gpu.jammy.list")
            dockerfile.run('apt-get update')
            dockerfile.run('apt-get install -y \
                            intel-opencl-icd intel-level-zero-gpu level-zero \
                            intel-media-va-driver-non-free libmfx1 libmfxgen1 libvpl2 \
                            libegl-mesa0 libegl1-mesa libegl1-mesa-dev libgbm1 libgl1-mesa-dev libgl1-mesa-dri \
                            libglapi-mesa libgles2-mesa-dev libglx-mesa0 libigdgmm12 libxatracker2 mesa-va-drivers \
                            mesa-vdpau-drivers mesa-vulkan-drivers va-driver-all')
            # Dev libraries
            dockerfile.run('apt-get install -y \
                            libigc-dev \
                            intel-igc-cm \
                            libigdfcl-dev \
                            libigfxcmrt-dev \
                            level-zero-dev')
        else:
            print("Intel GPU drivers do not currently support 24.04 in WSL")
    
def install_opencl_intercept_layer(dockerfile: Dockerfile):
    dockerfile.run("git clone https://github.com/intel/opencl-intercept-layer.git /opencl-intercept-layer")
    dockerfile.workdir("/opencl-intercept-layer")
    dockerfile.run("git checkout v3.0.6 && mkdir build")
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

    if "intel" in args.tag:
        dockerfile.userswitch("root")
        dockerfile.run('addgroup render')
        dockerfile.run("usermod -a -G render,video ubuntu")
        dockerfile.userswitch("ubuntu")

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
    install_cuda_dsmlp(dockerfile, args)

    if "arm64" in args.tag or "cuda" in args.tag:
        install_pocl(dockerfile, args)
        
    # install_cuda_drivers(dockerfile, args)
    install_intelGPU_drivers(dockerfile, args)
    install_opencl_intercept_layer(dockerfile)
    install_cl_blast(dockerfile)

    configure_user(dockerfile, args)
    
    dockerfile.cmd("/bin/bash")

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(str(dockerfile))

if __name__ == "__main__":
    main()

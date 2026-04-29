"""Ported from ivpm.setup.install_lib with updated import paths."""
import os
import platform
import shutil
from setuptools.command.install_lib import install_lib as _install_lib

from ivpm_build.setup.ivpm_data import (
    get_ivpm_extra_data,
    get_ivpm_ext_name_m,
    expand_libvars,
)


class InstallLib(_install_lib):

    def install(self):
        ivpm_extra_data = get_ivpm_extra_data()
        print("ivpm_extra_data=%s" % str(ivpm_extra_data))

        install_root = self.get_finalized_command("install").root

        if install_root is None:
            return

        build_py = self.get_finalized_command("build_py")
        for p in build_py.packages:
            if p in ivpm_extra_data.keys():
                for spec in ivpm_extra_data[p]:
                    src = expand_libvars(spec[0])
                    if not os.path.isabs(src):
                        src = os.path.join(os.getcwd(), src)
                    if not os.path.isfile(src) and not os.path.isdir(src):
                        for libdir in ["lib", "lib64"]:
                            src_t = expand_libvars(spec[0], libdir=libdir)
                            print("Try src_t: %s" % src_t)
                            if os.path.isfile(src_t) or os.path.isdir(src_t):
                                print("... Found")
                                src = src_t
                                break
                    print("src: %s" % src)
                    dst = spec[1]

                    if not os.path.isfile(src) and not os.path.isdir(src):
                        for libdir in ["lib", "lib64"]:
                            src_t = expand_libvars(spec[0], libdir=libdir)
                            if os.path.isfile(src_t) or os.path.isdir(src_t):
                                src = src_t
                                break

                    if os.path.isfile(src):
                        dst_file = os.path.join(
                            install_root, p, dst, os.path.basename(src)
                        )
                        dst_dir = os.path.dirname(dst_file)
                        if not os.path.isdir(dst_dir):
                            os.makedirs(dst_dir)
                        shutil.copyfile(src, dst_file)

                        if "{dllext}" in spec[0] and platform.system() == "Windows":
                            link_lib = src.replace(".dll", ".lib")
                            print("Test link_lib: %s" % link_lib)
                            if os.path.isfile(link_lib):
                                print("Found")
                                shutil.copyfile(
                                    link_lib,
                                    os.path.join(
                                        install_root, p, dst, os.path.basename(link_lib)
                                    ),
                                )
                            else:
                                print("Not Found")
                    elif os.path.isdir(src):
                        dst_dir = os.path.join(
                            install_root, p, dst, os.path.basename(src)
                        )
                        if not os.path.isdir(dst_dir):
                            os.makedirs(dst_dir, exist_ok=True)
                        shutil.copytree(src, dst_dir, dirs_exist_ok=True)
                    else:
                        raise Exception('Source path "%s" doesn\'t exist' % src)
                    print("Copy: %s" % str(spec))

        print("--> super.install")
        ret = super().install()
        print("<-- super.install")
        return ret

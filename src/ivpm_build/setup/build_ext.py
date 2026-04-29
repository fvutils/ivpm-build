"""Ported from ivpm.setup.BuildExt with distutils.file_util replaced by shutil
and cmake logic delegated to CmakeBuilder.
"""
import os
import shutil
from setuptools.command.build_ext import build_ext as _build_ext

import ivpm_build.setup.ivpm_data as idata
from ivpm_build.cmake.cmake_builder import CmakeBuilder


class BuildExt(_build_ext):

    def build_extensions(self):
        proj_dir = os.getcwd()

        if os.path.isfile(os.path.join(proj_dir, "CMakeLists.txt")):
            print("build_cmake")
            debug = False
            import sys
            if "-DDEBUG" in sys.argv:
                debug = True
            elif os.environ.get("DEBUG", "") in ("1", "y", "Y"):
                debug = True
            CmakeBuilder(proj_dir, debug=debug).run()

            for src, dst in idata.get_ivpm_extdep_data():
                shutil.copyfile(src, dst)

        super().build_extensions()

    def build_extension(self, ext):
        proj_dir = os.getcwd()
        print("build_extension: %s" % str(ext))
        include_dirs = getattr(ext, "include_dirs", [])
        setattr(ext, "include_dirs", include_dirs)

        ret = super().build_extension(ext)

        build_py = self.get_finalized_command("build_py")
        ext_name_m = idata.get_ivpm_ext_name_m()

        for ext in self.extensions:
            print("Ext: %s" % str(ext))
            fullname = self.get_ext_fullname(ext.name)
            filename = self.get_ext_filename(fullname)

            print("fullname=%s filename=%s" % (fullname, filename), flush=True)

            modpath = fullname.split(".")

            if fullname in ext_name_m.keys():
                mapped_filename = idata.expand_libvars(ext_name_m[fullname])
                dest_filename = os.path.join(
                    self.build_lib, "/".join(modpath[:-1]), mapped_filename
                )
            else:
                dest_filename = os.path.join(self.build_lib, filename)
            src_filename = os.path.join(self.build_lib, filename)

            print("dest_filename: %s src_filename: %s" % (dest_filename, src_filename))
            if src_filename != dest_filename:
                os.rename(src_filename, dest_filename)

        return ret

    def copy_extensions_to_source(self):
        """Like the base class method, but copy libs into proper directory in develop."""
        print("copy_extensions_to_source")
        for hook in idata.get_hooks(idata.Phase_BuildPre):
            hook(self)

        build_py = self.get_finalized_command("build_py")
        ext_name_m = idata.get_ivpm_ext_name_m()

        for ext in self.extensions:
            fullname = self.get_ext_fullname(ext.name)
            filename = self.get_ext_filename(fullname)

            print("fullname=%s filename=%s" % (fullname, filename), flush=True)

            modpath = fullname.split(".")
            package = ".".join(modpath[:-1])
            package_dir = build_py.get_package_dir(package)

            if fullname in ext_name_m.keys():
                mapped_filename = idata.expand_libvars(ext_name_m[fullname])
                dest_filename = os.path.join(package_dir, mapped_filename)
                src_filename = os.path.join(
                    self.build_lib, "/".join(modpath[:-1]), mapped_filename
                )
            else:
                dest_filename = os.path.join(package_dir, os.path.basename(filename))
                src_filename = os.path.join(self.build_lib, filename)

            os.makedirs(os.path.dirname(dest_filename), exist_ok=True)

            if not self.dry_run:
                shutil.copy2(src_filename, dest_filename)

        for hook in idata.get_hooks(idata.Phase_BuildPost):
            hook(self)

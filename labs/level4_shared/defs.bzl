"""py_layered_binary: hand a py_binary to rules_img as three layers instead of one.

`pkg_tar(include_runfiles = True)` packs everything a py_binary needs (the
interpreter, the pip wheels, your .py files) into ONE tar. Two services with
the same interpreter therefore share nothing: each tar also holds its own app
code, so the digests never match.

This rule re-exports a py_binary and sorts its runfiles into three named groups
(the rules_runfiles_group protocol). rules_img's `layer_from_binary` reads the
groups and builds one layer per group, lowest rank first:

    rank -2  interpreter   python-build-standalone, from the Python toolchain
    rank -1  third_party   every file from another repo: the pip wheels
    rank  0  app           your code and the launcher (changes every commit)

Byte-identical groups give byte-identical layers, so every image built from the
same interpreter and wheels shares those layers.
"""

load("@rules_runfiles_group//runfiles_group:lib.bzl", "lib")
load("@rules_runfiles_group//runfiles_group:providers.bzl", "RunfilesGroupInfo", "RunfilesGroupMetadataInfo")

_PY_TOOLCHAIN = "@bazel_tools//tools/python:toolchain_type"

def _py_layered_binary_impl(ctx):
    runfiles = ctx.attr.binary[DefaultInfo].default_runfiles
    runtime = ctx.toolchains[_PY_TOOLCHAIN].py3_runtime
    interpreter_files = {f: True for f in runtime.files.to_list()}

    interpreter, third_party, app = [], [], []
    for f in runfiles.files.to_list():
        if f in interpreter_files or f == runtime.interpreter:
            interpreter.append(f)
        elif f.owner and f.owner.repo_name:
            third_party.append(f)
        else:
            app.append(f)

    exe = ctx.actions.declare_file(ctx.label.name)
    ctx.actions.symlink(output = exe, target_file = ctx.executable.binary, is_executable = True)

    return [
        DefaultInfo(
            executable = exe,
            runfiles = ctx.runfiles(files = [exe]).merge(runfiles),
        ),
        RunfilesGroupInfo(**{
            "bwb#interpreter": ctx.runfiles(files = interpreter),
            "bwb#third_party": ctx.runfiles(files = third_party),
            "bwb#app": ctx.runfiles(files = app + [exe]).merge(ctx.runfiles(
                symlinks = runfiles.symlinks,
                root_symlinks = runfiles.root_symlinks,
            )),
        }),
        RunfilesGroupMetadataInfo(groups = {
            "bwb#interpreter": lib.group_metadata(rank = -2, do_not_merge = True),
            "bwb#third_party": lib.group_metadata(rank = -1),
            "bwb#app": lib.group_metadata(rank = 0, executable_group = True),
        }),
    ]

py_layered_binary = rule(
    implementation = _py_layered_binary_impl,
    doc = "A py_binary whose runfiles rules_img can split into interpreter / third_party / app layers.",
    attrs = {
        "binary": attr.label(
            doc = "The py_binary to wrap. Set legacy_create_init = 0 on it: generated empty __init__.py files can't be put in a group.",
            executable = True,
            cfg = "target",
            mandatory = True,
        ),
    },
    executable = True,
    toolchains = [_PY_TOOLCHAIN],
)

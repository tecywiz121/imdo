#include <seccomp.h>
#include <errno.h>
#include <Python.h>

static int disable_setsid(void) {
    scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_ALLOW);
    if (!ctx) {
        return 1;
    }

    if (seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM), SCMP_SYS(setsid), 0)) {
        return 1;
    }

    if (seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EPERM), SCMP_SYS(setpgid), 0)) {
        return 1;
    }

    if (seccomp_load(ctx)) {
        return 1;
    }

    return 0;
}

static PyObject *imdo_disable_setsid(PyObject* self) {
    return Py_BuildValue("i", disable_setsid());
}

static PyMethodDef module_methods[] = {
    {"disable_setsid", (PyCFunction)imdo_disable_setsid, METH_NOARGS, NULL},
    {0},
};

PyMODINIT_FUNC init_imdo(void) {
    (void) Py_InitModule("_imdo", module_methods);
}

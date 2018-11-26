import os
import py_compile
import marshal
import iutil
import pickle
import sys
import imp
from collections import OrderedDict
import traceback

REJECT_LIMIT = 10

modules = OrderedDict()

def collectModuleFiles(path):
    for root, dirs, files in os.walk(path):
        for phile in files:
            _, ext = os.path.splitext(phile)
            ext = ext.lower()
            if ext == '.py':
                compileModuleFile(path, os.path.join(root, phile))
            else:
                pass

def compileModuleFile(path, filename):
    py_compile.compile(filename, doraise=True)
    with open(filename + 'c', 'rb') as pycfile:
        data = pycfile.read()[8:]
        rel_path = os.path.relpath(filename, path)
        rel_path, ext = os.path.splitext(rel_path)
        packages = iutil.splitPath(rel_path)
        isPackage = False
        if packages[-1] == '__init__':
            packages = packages[:-1]
            isPackage = True
        packages.insert(0, os.path.basename(path))
        modules['.'.join(packages)] = (data, isPackage)

def generateInstallerData(path, dataPath):
    collectModuleFiles(path)
    data = pickle.dumps(modules)
    with open(dataPath, 'wb') as datafile:
        datafile.write(data)

def installData(resource_root, datafile):
    data = None
    missing_packages = []
    with open(datafile, 'rb') as datafile1:
        data = datafile1.read()
        data = pickle.loads(data)
    if data:
        reject_count = {}
        modulenames = data.keys()

        for mn in modulenames:
            sys.modules[mn] = imp.new_module(mn)

        while modulenames:

            modulename = modulenames.pop(0)
            binaryData, isPackage = data[modulename]

            #sys.modules[modulename] = imp.new_module(modulename)
            main_package = modulename.split('.')
            if isPackage:
                sys.modules[modulename].__path__ = os.path.join(
                        resource_root, *main_package)
                main_package.append('__init__')
            sys.modules[modulename].__file__ = os.path.join(
                    resource_root, *main_package)+'.pyc'
            code = marshal.loads(binaryData)
            try:
                exec code in sys.modules[modulename].__dict__
                parentModule = '.'.join(modulename.split('.')[:-1])
                if parentModule:
                    setattr(sys.modules[parentModule], modulename.split('.')[-1],
                            sys.modules[modulename])
            except (ImportError, AttributeError) as e:
                print modulename
                traceback.print_exc()
                rc = reject_count.get(modulename, 0)
                if rc < REJECT_LIMIT:
                    reject_count[modulename] = rc + 1
                    modulenames.append(modulename)
                else:
                    print 'RC limit exceeded for %s' % modulename
                    traceback.print_exc()
                    del sys.modules[modulename]
            else:
                print modulename, 'DONE'

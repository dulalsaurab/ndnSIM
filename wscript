# -*- Mode: python; py-indent-offset: 4; indent-tabs-mode: nil; coding: utf-8; -*-
#
# Copyright (c) 2014, Regents of the University of California
#
# GPL 3.0 license, see the COPYING.md file for more information
#

VERSION = '0.1.0'
APPNAME = "nfd"
BUGREPORT = "http://redmine.named-data.net/projects/nfd"
URL = "https://github.com/named-data/NFD"

from waflib import Logs
import os

def options(opt):
    opt.load('compiler_cxx gnu_dirs')
    opt.load('boost doxygen coverage unix-socket default-compiler-flags',
             tooldir=['.waf-tools'])

    nfdopt = opt.add_option_group('NFD Options')
    nfdopt.add_option('--with-tests', action='store_true', default=False,
                      dest='with_tests', help='''Build unit tests''')

def configure(conf):
    conf.load("compiler_cxx boost gnu_dirs")

    try: conf.load("doxygen")
    except: pass

    conf.load('default-compiler-flags')

    conf.check_cfg(package='libndn-cpp-dev', args=['--cflags', '--libs'],
                   uselib_store='NDN_CPP', mandatory=True)

    boost_libs = 'system chrono program_options'
    if conf.options.with_tests:
        conf.env['WITH_TESTS'] = 1
        conf.define('WITH_TESTS', 1);
        boost_libs += ' unit_test_framework'

    conf.check_boost(lib=boost_libs)

    if conf.env.BOOST_VERSION_NUMBER < 104800:
        Logs.error("Minimum required boost version is 1.48.0")
        Logs.error("Please upgrade your distribution or install custom boost libraries" +
                   " (http://redmine.named-data.net/projects/nfd/wiki/Boost_FAQ)")
        return

    conf.load('unix-socket')

    conf.check_cxx(lib='rt', uselib_store='RT',
                   define_name='HAVE_RT', mandatory=False)

    if conf.check_cxx(lib='pcap', uselib_store='PCAP',
                      define_name='HAVE_PCAP', mandatory=False):
        conf.env['HAVE_PCAP'] = True

    conf.check_cxx(lib='resolv', uselib_store='RESOLV', mandatory=False)

    conf.load('coverage')

    conf.define('DEFAULT_CONFIG_FILE', '%s/ndn/nfd.conf' % conf.env['SYSCONFDIR'])

    conf.write_config_header('daemon/config.hpp')

def build(bld):
    nfd_objects = bld(
        target='nfd-objects',
        features='cxx',
        source=bld.path.ant_glob(['daemon/**/*.cpp'],
                                 excl=['daemon/face/ethernet-*.cpp',
                                       'daemon/face/unix-*.cpp',
                                       'daemon/main.cpp']),
        use='BOOST NDN_CPP RT',
        includes='. daemon',
        )

    if bld.env['HAVE_PCAP']:
        nfd_objects.source += bld.path.ant_glob('daemon/face/ethernet-*.cpp')
        nfd_objects.use += ' PCAP'

    if bld.env['HAVE_UNIX_SOCKETS']:
        nfd_objects.source += bld.path.ant_glob('daemon/face/unix-*.cpp')

    bld(target='nfd',
        features='cxx cxxprogram',
        source='daemon/main.cpp',
        use='nfd-objects',
        includes='. daemon',
        )

    for app in bld.path.ant_glob('tools/*.cpp'):
        bld(features=['cxx', 'cxxprogram'],
            target='bin/%s' % (str(app.change_ext(''))),
            source=['tools/%s' % (str(app))],
            includes='. daemon',
            use='nfd-objects RESOLV',
            )

    # Unit tests
    if bld.env['WITH_TESTS']:
        unit_tests = bld.program(
            target='unit-tests',
            features='cxx cxxprogram',
            source=bld.path.ant_glob(['tests/**/*.cpp'],
                                     excl=['tests/face/ethernet.cpp',
                                           'tests/face/unix-*.cpp']),
            use='nfd-objects',
            includes='. daemon',
            install_prefix=None,
          )

        if bld.env['HAVE_PCAP']:
            unit_tests.source += bld.path.ant_glob('tests/face/ethernet.cpp')

        if bld.env['HAVE_UNIX_SOCKETS']:
            unit_tests.source += bld.path.ant_glob('tests/face/unix-*.cpp')

    bld(features="subst",
        source='nfd.conf.sample.in',
        target='nfd.conf.sample',
        install_path="${SYSCONFDIR}/ndn")

    bld(features='subst',
        source='tools/nfd-status-http-server.py',
        target='nfd-status-http-server',
        install_path="${BINDIR}",
        chmod=0755)

def doxygen(bld):
    if not bld.env.DOXYGEN:
        bld.fatal("ERROR: cannot build documentation (`doxygen' is not found in $PATH)")
    bld(features="doxygen",
        doxyfile='docs/doxygen.conf')

# search packages used by KDE
find_package(KDE4 REQUIRED)
include(KDE4Defaults)
include(MacroLibrary)

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} )

INCLUDE(PythonMacros)

macro_optional_find_package(PythonLibrary)
macro_optional_find_package(SIP)

macro_optional_find_package(PyQt4)
IF(NOT PYQT4_FOUND)
    macro_log_feature(PYQT4_FOUND "PyQt4" "PyQt4 was not found.  It is needed by userconfig to run. (Use -DINSTALL_USERCONFIG=TRUE to install anyway)" "http://www.riverbankcomputing.co.uk/pyqt/" FALSE)
ENDIF(NOT PYQT4_FOUND)

macro_optional_find_package(PyKDE4)
IF(NOT PYKDE4_FOUND)
    macro_log_feature(PYKDE_FOUND "PyKDE4" "PyKDE4 was not found.  It is needed by userconfig to run.  (Use -DINSTALL_USERCONFIG=TRUE to install anyway)" "http://websvn.kde.org/trunk/KDE/kdebindings/python/pykde4/" FALSE)
ENDIF(NOT PYKDE4_FOUND)

IF(PYQT4_FOUND AND PYKDE4_FOUND)
    SET(INSTALL_USERCONFIG TRUE)
ENDIF(PYQT4_FOUND AND PYKDE4_FOUND)

IF(INSTALL_USERCONFIG)
    install ( FILES
        __init__.py
        userconfig.py
        user_dialogs.py
        group_dialogs.py
        models.py
        DESTINATION ${DATA_INSTALL_DIR}/userconfig/ )
    install (FILES
        util/__init__.py
        util/unixauthdb.py
        DESTINATION ${DATA_INSTALL_DIR}/userconfig/util/ )
    install( FILES
        ui/deleteuser.ui
        ui/groups.ui
        ui/overwritehomedirectory.ui
        ui/userproperties-details.ui
        ui/userproperties-privgroups.ui
        ui/userproperties-pwsec.ui
        ui/users.ui
        DESTINATION ${DATA_INSTALL_DIR}/userconfig/ui/ )
    install(FILES userconfig.desktop DESTINATION ${SERVICES_INSTALL_DIR})
    KDE4_CREATE_HANDBOOK( doc/userconfig/index.docbook )
    install(FILES
        doc/userconfig/index.docbook
        ${CMAKE_CURRENT_BINARY_DIR}/index.cache.bz2
        DESTINATION ${HTML_INSTALL_DIR}/en/userconfig/ )
ENDIF(INSTALL_USERCONFIG)
find_package(Msgfmt REQUIRED)
find_package(Gettext REQUIRED)

macro_display_feature_log()

find_package( KDE4 REQUIRED )

set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${CMAKE_CURRENT_SOURCE_DIR}/cmake-modules )

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
    python_install(__init__.py ${DATA_INSTALL_DIR}/userconfig/)
    python_install(userconfig.py ${DATA_INSTALL_DIR}/userconfig/)
    python_install(user_dialogs.py ${DATA_INSTALL_DIR}/userconfig/)
    python_install(group_dialogs.py ${DATA_INSTALL_DIR}/userconfig/)
    python_install(models.py ${DATA_INSTALL_DIR}/userconfig/)
    python_install(util/__init__.py ${DATA_INSTALL_DIR}/userconfig/util/)
    python_install(util/unixauthdb.py ${DATA_INSTALL_DIR}/userconfig/util/)
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
ENDIF(INSTALL_USERCONFIG)

macro_display_feature_log()
cmake_minimum_required(VERSION 3.16)

project(InlineDataAnalytics VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets Charts PrintSupport)

qt_standard_project_setup()

set(PROJECT_SOURCES
    main.cpp
    dataframe.h
    dataframe.cpp
    fileloaders.h
    fileloaders.cpp
    smoothing.h
    smoothing.cpp
    curvefit.h
    curvefit.cpp
    mainwindow.h
    mainwindow.cpp
    leftpanel.h
    leftpanel.cpp
    rightpanel.h
    rightpanel.cpp
    menubar.h
    menubar.cpp
    toolbar.h
    toolbar.cpp
    axisselection.h
    axisselection.cpp
    smoothingoptions.h
    smoothingoptions.cpp
    datafilter.h
    datafilter.cpp
    curvefittingwidget.h
    curvefittingwidget.cpp
    commentbox.h
    commentbox.cpp
    plotarea.h
    plotarea.cpp
    statisticsarea.h
    statisticsarea.cpp
    sessionmanager.h
    sessionmanager.cpp
    sheetselectiondialog.h
    sheetselectiondialog.cpp
)

qt_add_executable(InlineDataAnalytics ${PROJECT_SOURCES})

target_link_libraries(InlineDataAnalytics PRIVATE
    Qt6::Widgets
    Qt6::Charts
    Qt6::PrintSupport
)

install(TARGETS InlineDataAnalytics
    BUNDLE DESTINATION .
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

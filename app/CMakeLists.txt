cmake_minimum_required(VERSION 3.20.0)

set(APPLICATION_CONFIG_DIR "${CMAKE_CURRENT_LIST_DIR}/conf")

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(project)

add_link_options(--print-memory-usage,-Map=${PROJECT_BINARY_DIR}/${PROJECT_NAME}.map)

target_include_directories(app PRIVATE src)

if(CONFIG_TRACKER_ORACLE_MODE)
    target_sources(app PRIVATE src/oracle_main.c)
else()
    target_sources(app PRIVATE src/main.c)
endif()
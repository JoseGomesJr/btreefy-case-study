if(CONFIG_TRACKER_COMMON)
    zephyr_library_named(tracker_common)

    # Global (not library-scoped) so tracker_bt/tracker_fsm can #include
    # "tracker/*.h" too.
    zephyr_include_directories(include)

    zephyr_library_sources(
        src/tracker_events.c
        src/tracker_bb.c
        src/drivers_fake.c
    )

    zephyr_library_sources_ifdef(CONFIG_TRACKER_TRACE src/trace_probe.c)

    zephyr_library_link_libraries(zephyr_interface)
endif()

if(CONFIG_TRACKER_POLICY_FSM)
    zephyr_library_named(tracker_fsm)

    if(CONFIG_TRACKER_WITH_TAMPER)
        zephyr_library_sources(src/tracker_fsm_states_tamper.c)
    else()
        zephyr_library_sources(src/tracker_fsm_states_base.c)
    endif()

    zephyr_library_sources(
        src/tracker_fsm_policy.c
    )

    zephyr_library_link_libraries(zephyr_interface)
endif()

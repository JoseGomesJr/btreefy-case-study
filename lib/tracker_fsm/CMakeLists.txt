if(CONFIG_TRACKER_POLICY_FSM)
    zephyr_library_named(tracker_fsm)

    zephyr_library_sources(
        src/tracker_fsm_states.c
        src/tracker_fsm_policy.c
    )

    zephyr_library_link_libraries(zephyr_interface)
endif()

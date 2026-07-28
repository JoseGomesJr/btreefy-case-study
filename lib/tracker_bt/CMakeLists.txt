if(CONFIG_TRACKER_POLICY_BT)
    zephyr_library_named(tracker_bt)

    set(BTF_PARSER ${ZEPHYR_BTREEFY_MODULE_DIR}/scripts/btf_groot_parser.py)
    set(BTF_GEN_DIR ${CMAKE_CURRENT_BINARY_DIR}/generated)

    # CONFIG_TRACKER_WITH_TAMPER picks which model gets compiled in — the
    # base tree is untouched by the tamper variant (see
    # models/tracker_tamper.xml), no #ifdef inside the XML itself.
    if(CONFIG_TRACKER_WITH_TAMPER)
        set(BTF_MODEL ${CMAKE_CURRENT_SOURCE_DIR}/../../models/tracker_tamper.xml)
        set(BTF_TREE_NAME tracker_tamper)
    else()
        set(BTF_MODEL ${CMAKE_CURRENT_SOURCE_DIR}/../../models/tracker_base.xml)
        set(BTF_TREE_NAME tracker_base)
    endif()

    file(MAKE_DIRECTORY ${BTF_GEN_DIR})

    # btf_nodes_generated.[ch] are regenerated on every build from the Groot
    # XML — never hand-edit them (CLAUDE.md rule 1).
    add_custom_command(
        OUTPUT ${BTF_GEN_DIR}/btf_nodes_generated.c ${BTF_GEN_DIR}/btf_action_functions_generated.h
        COMMAND ${Python3_EXECUTABLE} ${BTF_PARSER}
                -m ${BTF_MODEL} -tn ${BTF_TREE_NAME}
                --source-output-dir ${BTF_GEN_DIR} --include-output-dir ${BTF_GEN_DIR}
        DEPENDS ${BTF_MODEL} ${BTF_PARSER}
        COMMENT "Generating ${BTF_TREE_NAME} BT nodes from ${BTF_MODEL}"
    )

    zephyr_library_include_directories(${BTF_GEN_DIR})

    zephyr_library_sources(
        ${BTF_GEN_DIR}/btf_nodes_generated.c
        src/tracker_bt_actions.c
        src/tracker_bt_policy.c
    )

    zephyr_library_link_libraries(zephyr_interface)
    zephyr_library_link_libraries(BTreeFy-Src)
endif()

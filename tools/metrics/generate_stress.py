import os
from pathlib import Path

DEPTH = 5
INTERNAL_NODES = (1 << DEPTH) - 1
LEAF_NODES = (1 << DEPTH)

REPO_ROOT = Path(__file__).resolve().parents[2]
STRESS_DIR = REPO_ROOT / "tests" / "stress_app"
MODELS_DIR = REPO_ROOT / "models"
SRC_DIR = STRESS_DIR / "src"

def generate_fsm():
    h_code = """#pragma once
#include <zephyr/smf.h>
extern struct smf_ctx stress_fsm_ctx;
void init_stress_fsm(void);
void run_stress_fsm(int ev_val);
"""
    c_code = """#include <zephyr/kernel.h>
#include <zephyr/smf.h>
#include "fsm_stress.h"

struct smf_ctx stress_fsm_ctx;
static int current_ev_val = 0;
"""

    # Generate state declarations
    c_code += "static const struct smf_state demo_states[];\n"
    c_code += "enum demo_state { S_IDLE, " + ", ".join([f"S_COND_{i}" for i in range(1, INTERNAL_NODES + 1)]) + ", " + ", ".join([f"S_ACT_{i}" for i in range(INTERNAL_NODES + 1, INTERNAL_NODES + LEAF_NODES + 1)]) + " };\n\n"

    # Generate state functions
    c_code += "static enum smf_state_result s_idle_run(void *o) {\n    if(current_ev_val > 0) smf_set_state(SMF_CTX(&stress_fsm_ctx), &demo_states[S_COND_1]);\n    return SMF_EVENT_HANDLED;\n}\n\n"

    for i in range(1, INTERNAL_NODES + 1):
        left = 2 * i
        right = 2 * i + 1
        left_state = f"S_COND_{left}" if left <= INTERNAL_NODES else f"S_ACT_{left}"
        right_state = f"S_COND_{right}" if right <= INTERNAL_NODES else f"S_ACT_{right}"
        
        c_code += f"static enum smf_state_result s_cond_{i}_run(void *o) {{\n"
        c_code += f"    if (current_ev_val % {i+1} == 0) {{\n"
        c_code += f"        smf_set_state(SMF_CTX(&stress_fsm_ctx), &demo_states[{left_state}]);\n"
        c_code += f"    }} else {{\n"
        c_code += f"        smf_set_state(SMF_CTX(&stress_fsm_ctx), &demo_states[{right_state}]);\n"
        c_code += f"    }}\n    return SMF_EVENT_HANDLED;\n}}\n\n"

    for i in range(INTERNAL_NODES + 1, INTERNAL_NODES + LEAF_NODES + 1):
        c_code += f"static enum smf_state_result s_act_{i}_run(void *o) {{\n"
        c_code += f"    // Action {i}\n"
        c_code += f"    smf_set_state(SMF_CTX(&stress_fsm_ctx), &demo_states[S_IDLE]);\n"
        c_code += f"    return SMF_EVENT_HANDLED;\n"
        c_code += f"}}\n\n"

    # Generate state array
    c_code += "static const struct smf_state demo_states[] = {\n"
    c_code += "    [S_IDLE] = SMF_CREATE_STATE(NULL, s_idle_run, NULL, NULL, NULL),\n"
    for i in range(1, INTERNAL_NODES + 1):
        c_code += f"    [S_COND_{i}] = SMF_CREATE_STATE(NULL, s_cond_{i}_run, NULL, NULL, NULL),\n"
    for i in range(INTERNAL_NODES + 1, INTERNAL_NODES + LEAF_NODES + 1):
        c_code += f"    [S_ACT_{i}] = SMF_CREATE_STATE(NULL, s_act_{i}_run, NULL, NULL, NULL),\n"
    c_code += "};\n\n"

    c_code += """void init_stress_fsm(void) {
    smf_set_initial(SMF_CTX(&stress_fsm_ctx), &demo_states[S_IDLE]);
}

void run_stress_fsm(int ev_val) {
    current_ev_val = ev_val;
    smf_run_state(SMF_CTX(&stress_fsm_ctx));
}
"""
    
    (SRC_DIR / "fsm_stress.h").write_text(h_code)
    (SRC_DIR / "fsm_stress.c").write_text(c_code)

def generate_fsm_diagram():
    mermaid = "```mermaid\\nstateDiagram-v2\\n"
    mermaid += "    S_IDLE --> S_COND_1 : Event > 0\\n"
    for i in range(1, INTERNAL_NODES + 1):
        left = 2 * i
        right = 2 * i + 1
        left_state = f"S_COND_{left}" if left <= INTERNAL_NODES else f"S_ACT_{left}"
        right_state = f"S_COND_{right}" if right <= INTERNAL_NODES else f"S_ACT_{right}"
        mermaid += f"    S_COND_{i} --> {left_state} : Event % {i+1} == 0\\n"
        mermaid += f"    S_COND_{i} --> {right_state} : Else\\n"
    
    for i in range(INTERNAL_NODES + 1, INTERNAL_NODES + LEAF_NODES + 1):
        mermaid += f"    S_ACT_{i} --> S_IDLE : Done\\n"
    
    mermaid += "```\\n"
    artifact_path = Path("/home/victor/.gemini/antigravity-cli/brain/26374394-7861-4819-9406-ad85ee91ac7b/fsm_diagram.md")
    artifact_path.write_text(f"# FSM Diagram (Depth {DEPTH})\\n\\n{mermaid}")

def generate_bt():
    def build_node(i):
        if i > INTERNAL_NODES:
            return f'<Script name="Act{i}" code="act{i}"/>'
        
        left = build_node(2 * i)
        right = build_node(2 * i + 1)
        
        return f"""<Fallback name="Decision_{i}">
    <Sequence name="Seq_{i}">
        <ScriptCondition name="Cond{i}" code="cond{i}"/>
        {left}
    </Sequence>
    {right}
</Fallback>"""

    xml = f"""<?xml version="1.0"?>
<root main_tree_to_execute="BehaviorTree">
    <BehaviorTree ID="BehaviorTree">
        {build_node(1)}
    </BehaviorTree>
    <TreeNodesModel>
"""
    for i in range(1, INTERNAL_NODES + 1):
        xml += f'        <ScriptCondition ID="Cond{i}"/>\n'
    for i in range(INTERNAL_NODES + 1, INTERNAL_NODES + LEAF_NODES + 1):
        xml += f'        <Script ID="Act{i}"/>\n'
    xml += """    </TreeNodesModel>
</root>
"""
    (MODELS_DIR / "stress_bt.xml").write_text(xml)

    # Generate BT actions C code
    c_code = """#include <zephyr/kernel.h>
#include "btreefy/btreefy.h"

extern int current_ev_val;
"""
    for i in range(1, INTERNAL_NODES + 1):
        c_code += f"""enum btf_node_status cond{i}(struct btf_tree *tree) {{
    return (current_ev_val % {i+1} == 0) ? BTF_SUCCESS_STATUS : BTF_FAILURE_STATUS;
}}
"""
    for i in range(INTERNAL_NODES + 1, INTERNAL_NODES + LEAF_NODES + 1):
        c_code += f"""enum btf_node_status act{i}(struct btf_tree *tree) {{
    return BTF_SUCCESS_STATUS;
}}
"""
    (SRC_DIR / "bt_stress_actions.c").write_text(c_code)


def generate_main():
    main_code = """#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include "fsm_stress.h"
#include "btreefy/btreefy.h"

#ifdef CONFIG_ARCH_POSIX
#define _POSIX_C_SOURCE 200809L
#include <zephyr/posix/posix_time.h>
#include "posix_board_if.h"
static inline uint64_t bench_get_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}
#else
#include <zephyr/timing/timing.h>
static inline uint64_t bench_get_ns(void) {
    return k_cyc_to_ns_floor64(timing_counter_get());
}
#endif

extern struct btf_node stress_nodes[];
extern size_t stress_nodes_size;
struct btf_tree stress_tree;
int current_ev_val = 0;

#define STACK_SIZE 4096
K_THREAD_STACK_DEFINE(fsm_stack_area, STACK_SIZE);
struct k_thread fsm_thread_data;
K_THREAD_STACK_DEFINE(bt_stack_area, STACK_SIZE);
struct k_thread bt_thread_data;

void fsm_thread(void *p1, void *p2, void *p3) {
    init_stress_fsm();
    
#ifndef CONFIG_ARCH_POSIX
    timing_init();
    timing_start();
#endif
    // Warm up
    for(int i = 0; i < 100; i++) {
        run_stress_fsm(i % 32);
    }
    
    for (int i = 0; i < 32; i++) {
        current_ev_val = i;
        uint64_t start = bench_get_ns();
        for (int iter = 0; iter < 1000; iter++) {
            run_stress_fsm(current_ev_val);
        }
        uint64_t end = bench_get_ns();
        printk("[FSM_NS_PER_ITER] %llu\\n", (end - start) / 1000);
    }
}

void bt_thread(void *p1, void *p2, void *p3) {
    btf_init(&stress_tree, stress_nodes, stress_nodes_size);
    
    // Warm up
    for(int i = 0; i < 100; i++) {
        current_ev_val = i % 32;
        btf_tick_tree(&stress_tree);
    }

    for (int i = 0; i < 32; i++) {
        current_ev_val = i;
        uint64_t start = bench_get_ns();
        for (int iter = 0; iter < 1000; iter++) {
            btf_tick_tree(&stress_tree);
        }
        uint64_t end = bench_get_ns();
        printk("[BT_NS_PER_ITER] %llu\\n", (end - start) / 1000);
    }
}

int main(void) {
    printk("Starting Stress Test...\\n");

    k_thread_create(&fsm_thread_data, fsm_stack_area,
                    K_THREAD_STACK_SIZEOF(fsm_stack_area),
                    fsm_thread,
                    NULL, NULL, NULL,
                    5, 0, K_NO_WAIT);
    k_thread_name_set(&fsm_thread_data, "fsm_stress_thr");

    k_thread_join(&fsm_thread_data, K_FOREVER);

    k_thread_create(&bt_thread_data, bt_stack_area,
                    K_THREAD_STACK_SIZEOF(bt_stack_area),
                    bt_thread,
                    NULL, NULL, NULL,
                    5, 0, K_NO_WAIT);
    k_thread_name_set(&bt_thread_data, "bt_stress_thr");

    k_thread_join(&bt_thread_data, K_FOREVER);

    printk("Stress test done.\\n");
#ifdef CONFIG_ARCH_POSIX
    posix_exit(0);
#endif
    return 0;
}
"""
    (SRC_DIR / "main.c").write_text(main_code)

def generate_cmake():
    cmake = """cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(stress_app)

target_sources(app PRIVATE 
    src/main.c 
    src/fsm_stress.c 
    src/bt_stress_actions.c
    src/btf_nodes_generated.c
)
target_link_libraries(app PRIVATE BTreeFy-Src)
target_include_directories(app PRIVATE ${ZEPHYR_BASE}/../modules/lib/btreefy/include)
"""
    (STRESS_DIR / "CMakeLists.txt").write_text(cmake)
    
    prj = """CONFIG_SMF=y
CONFIG_THREAD_NAME=y
CONFIG_TIMING_FUNCTIONS=y
CONFIG_TRACKER_COMMON=n
"""
    (STRESS_DIR / "prj.conf").write_text(prj)

def main():
    STRESS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    SRC_DIR.mkdir(parents=True, exist_ok=True)

    generate_fsm()
    generate_fsm_diagram()
    generate_bt()
    generate_main()
    generate_cmake()
    
    # We will generate the XML, but wait, the btf_nodes_generated.c needs to be generated by the Groot Parser,
    abs_src_dir = SRC_DIR.resolve()
    abs_model = MODELS_DIR.resolve() / "stress_bt.xml"
    print("Running groot parser...")
    os.system(f"uv run python3 ../../../modules/lib/btreefy/scripts/btf_groot_parser.py -m {abs_model} -tn BehaviorTree --source-output-dir {abs_src_dir}/ --include-output-dir {abs_src_dir}/")
    
    # Patch names to avoid conflicts with tracker_bt
    btf_c = SRC_DIR / "btf_nodes_generated.c"
    if btf_c.exists():
        content = btf_c.read_text()
        content = content.replace("struct btf_node nodes[]", "struct btf_node stress_nodes[]")
        content = content.replace("size_t nodes_size =", "size_t stress_nodes_size =")
        content = content.replace("sizeof(nodes)", "sizeof(stress_nodes)")
        content = content.replace("sizeof(nodes[0])", "sizeof(stress_nodes[0])")
        btf_c.write_text(content)

    print("Stress test environment generated in tests/stress_app")

if __name__ == "__main__":
    main()

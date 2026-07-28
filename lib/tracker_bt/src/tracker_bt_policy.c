#include <stddef.h>
#include <stdint.h>

#include <zephyr/kernel.h>
#include <zephyr/zbus/zbus.h>

#include "btreefy/btreefy.h"
#include "btreefy/btreefy_objs.h"
#include "tracker/tracker_bb.h"
#include "tracker/tracker_events.h"

extern struct btf_node nodes[];
extern size_t          nodes_size;

static struct btf_tree s_bt_tree;

static void tracker_bt_thread_entry(void *p1, void *p2, void *p3)
{
    ARG_UNUSED(p1);
    ARG_UNUSED(p2);
    ARG_UNUSED(p3);

    btf_init(&s_bt_tree, nodes, (uint32_t) nodes_size);
    btf_set_data(&s_bt_tree, &g_tracker_bb, sizeof(g_tracker_bb));

    const struct zbus_channel *chan;

    while (true)
    {
        if (zbus_sub_wait(&sub_policy, &chan, K_FOREVER) != 0)
        {
            continue;
        }

        tracker_bb_update(chan);
        btf_tick_tree(&s_bt_tree);
    }
}

K_THREAD_DEFINE(tracker_bt_thread, 2048, tracker_bt_thread_entry, NULL, NULL, NULL, 7, 0, 0);

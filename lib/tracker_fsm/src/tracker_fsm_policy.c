/**
 * Impl-FSM policy thread — the FSM-side counterpart of
 * lib/tracker_bt/src/tracker_bt_policy.c. Waits for any change on the
 * channels sub_policy observes, updates the shared blackboard, and steps
 * the state machine. tracker_fsm_step() is the only place that differs
 * from a plain smf_run_state() call, and it adds zero instrumentation
 * inside the states themselves — see the comment below.
 */

#include <stddef.h>

#include <zephyr/kernel.h>
#include <zephyr/smf.h>
#include <zephyr/zbus/zbus.h>

#include "tracker/tracker_bb.h"
#include "tracker/tracker_events.h"
#include "tracker_fsm_states.h"

struct tracker_fsm_ctx
{
    struct smf_ctx ctx;
};

static struct tracker_fsm_ctx s_fsm;

static inline int state_index(const struct smf_state *state)
{
    return (int) (state - tracker_fsm_states);
}

static void tracker_fsm_step(void)
{
    const struct smf_state *prev = s_fsm.ctx.current;

    smf_run_state(SMF_CTX(&s_fsm));

    if (IS_ENABLED(CONFIG_TRACKER_TRACE) && (s_fsm.ctx.current != prev))
    {
        printk("FSM_TR,%u,%d,%d\n", k_cycle_get_32(), state_index(prev),
               state_index(s_fsm.ctx.current));
    }
}

static void tracker_fsm_thread_entry(void *p1, void *p2, void *p3)
{
    ARG_UNUSED(p1);
    ARG_UNUSED(p2);
    ARG_UNUSED(p3);

    smf_set_initial(SMF_CTX(&s_fsm), &tracker_fsm_states[STATE_SLEEP]);

    const struct zbus_channel *chan;

    while (true)
    {
        if (zbus_sub_wait(&sub_policy, &chan, K_FOREVER) != 0)
        {
            continue;
        }

        tracker_bb_update(chan);
        tracker_fsm_step();
    }
}

K_THREAD_DEFINE(tracker_fsm_thread, 2048, tracker_fsm_thread_entry, NULL, NULL, NULL, 7, 0, 0);

#include "tracker_fsm_states.h"

#include <zephyr/kernel.h>
#include <zephyr/zbus/zbus.h>

#include "tracker/tracker_bb.h"
#include "tracker/tracker_events.h"

#ifdef CONFIG_TRACKER_WITH_TAMPER

#define TRACKER_FSM_TAMPER_GUARD(o)                                              \
    do                                                                          \
    {                                                                           \
        if (g_tracker_bb.tamper)                                                \
        {                                                                       \
            smf_set_state(SMF_CTX(o), &tracker_fsm_states[STATE_TAMPER_ALERT]); \
            return SMF_EVENT_HANDLED;                                           \
        }                                                                       \
    } while (0)
#else
#define TRACKER_FSM_TAMPER_GUARD(o) \
    do                              \
    {                               \
    } while (0)
#endif

#ifdef CONFIG_TRACKER_WITH_TAMPER

static void tamper_alert_entry(void *o)
{
    ARG_UNUSED(o);
    struct tracker_cmd cmd = {.op = CMD_SEND_ALERT};
    zbus_chan_pub(&chan_tracker_cmd, &cmd, K_NO_WAIT);
}

static enum smf_state_result tamper_alert_run(void *o)
{
    if (!g_tracker_bb.tamper)
    {
        smf_set_state(SMF_CTX(o), &tracker_fsm_states[STATE_SLEEP]);
    }
    return SMF_EVENT_HANDLED;
}

#endif  // CONFIG_TRACKER_WITH_TAMPER

static void sleep_entry(void *o)
{
    ARG_UNUSED(o);
    struct tracker_cmd cmd = {.op = CMD_SLEEP};
    zbus_chan_pub(&chan_tracker_cmd, &cmd, K_NO_WAIT);
}

static enum smf_state_result sleep_run(void *o)
{
    TRACKER_FSM_TAMPER_GUARD(o);

    if (g_tracker_bb.new_position_requested)
    {
        smf_set_state(SMF_CTX(o), &tracker_fsm_states[STATE_GNSS_FIX]);
    }
    return SMF_EVENT_HANDLED;
}

static void gnss_fix_entry(void *o)
{
    ARG_UNUSED(o);
    struct tracker_cmd cmd = {.op = CMD_FIX_START};
    zbus_chan_pub(&chan_tracker_cmd, &cmd, K_NO_WAIT);
}

static enum smf_state_result gnss_fix_run(void *o)
{
    TRACKER_FSM_TAMPER_GUARD(o);

    switch (g_tracker_bb.gnss_status)
    {
        case GNSS_FIX:
            smf_set_state(SMF_CTX(o), &tracker_fsm_states[STATE_SEND_POSITION]);
            break;
        case GNSS_FAIL:
            smf_set_state(SMF_CTX(o), &tracker_fsm_states[STATE_REGISTER_FAILURE]);
            break;
        case GNSS_BUSY:
        default:
            break;
    }
    return SMF_EVENT_HANDLED;
}

static void send_position_entry(void *o)
{
    ARG_UNUSED(o);
    struct tracker_cmd cmd = {.op = CMD_SEND_POS};
    zbus_chan_pub(&chan_tracker_cmd, &cmd, K_NO_WAIT);
}

static enum smf_state_result send_position_run(void *o)
{
    TRACKER_FSM_TAMPER_GUARD(o);

    switch (g_tracker_bb.radio_status)
    {
        case RADIO_OK:
            smf_set_state(SMF_CTX(o), &tracker_fsm_states[STATE_SLEEP]);
            break;
        case RADIO_FAIL:
            smf_set_state(SMF_CTX(o), &tracker_fsm_states[STATE_REGISTER_FAILURE]);
            break;
        case RADIO_BUSY:
        default:
            break;
    }
    return SMF_EVENT_HANDLED;
}

static void register_failure_entry(void *o)
{
    struct tracker_cmd cmd = {.op = CMD_LOG_FAIL};
    zbus_chan_pub(&chan_tracker_cmd, &cmd, K_NO_WAIT);
    smf_set_state(SMF_CTX(o), &tracker_fsm_states[STATE_SLEEP]);
}

const struct smf_state tracker_fsm_states[] = {
    [STATE_SLEEP]            = SMF_CREATE_STATE(sleep_entry, sleep_run, NULL, NULL, NULL),
    [STATE_GNSS_FIX]         = SMF_CREATE_STATE(gnss_fix_entry, gnss_fix_run, NULL, NULL, NULL),
    [STATE_SEND_POSITION]    = SMF_CREATE_STATE(send_position_entry, send_position_run, NULL,
                                                 NULL, NULL),
    [STATE_REGISTER_FAILURE] = SMF_CREATE_STATE(register_failure_entry, NULL, NULL, NULL, NULL),
#ifdef CONFIG_TRACKER_WITH_TAMPER
    [STATE_TAMPER_ALERT]     = SMF_CREATE_STATE(tamper_alert_entry, tamper_alert_run, NULL, NULL,
                                                 NULL),
#endif
};

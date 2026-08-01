#include <stdbool.h>
#include <stdint.h>

#include <zephyr/kernel.h>
#ifdef CONFIG_THREAD_ANALYZER
#include <zephyr/debug/thread_analyzer.h>
#endif

#include "tracker/drivers_fake.h"

enum oracle_event_kind
{
    EV_REQUEST_TOGGLE,
    EV_GNSS_FIX,
    EV_GNSS_FAIL,
    EV_RADIO_OK,
    EV_RADIO_FAIL,
#ifdef CONFIG_TRACKER_WITH_TAMPER
    EV_TAMPER_TOGGLE,
#endif
    EV_KIND_COUNT,
};

static uint32_t s_rng_state;

static uint32_t xorshift32(void)
{
    uint32_t x = s_rng_state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    s_rng_state = x;
    return x;
}

static uint32_t rand_range(uint32_t n)
{
    return xorshift32() % n;
}

int main(void)
{
    s_rng_state = CONFIG_TRACKER_ORACLE_SEED != 0 ? (uint32_t) CONFIG_TRACKER_ORACLE_SEED : 1;

    bool request_active = false;
#ifdef CONFIG_TRACKER_WITH_TAMPER
    bool tamper_active = false;
#endif

    printk("ORACLE_START,%d,%d\n", CONFIG_TRACKER_ORACLE_SEED, CONFIG_TRACKER_ORACLE_N_EVENTS);

    for (int i = 0; i < CONFIG_TRACKER_ORACLE_N_EVENTS; i++)
    {
        switch ((enum oracle_event_kind) rand_range(EV_KIND_COUNT))
        {
            case EV_REQUEST_TOGGLE:
                request_active = !request_active;
                printk("EV,%d,REQUEST,%d\n", i, request_active);
                fake_request_new_position(request_active);
                break;
            case EV_GNSS_FIX:
                printk("EV,%d,GNSS_FIX\n", i);
                fake_gnss_finish(GNSS_FIX, (struct gnss_fix){0});
                break;
            case EV_GNSS_FAIL:
                printk("EV,%d,GNSS_FAIL\n", i);
                fake_gnss_finish(GNSS_FAIL, (struct gnss_fix){0});
                break;
            case EV_RADIO_OK:
                printk("EV,%d,RADIO_OK\n", i);
                fake_radio_finish(RADIO_OK);
                break;
            case EV_RADIO_FAIL:
                printk("EV,%d,RADIO_FAIL\n", i);
                fake_radio_finish(RADIO_FAIL);
                break;
#ifdef CONFIG_TRACKER_WITH_TAMPER
            case EV_TAMPER_TOGGLE:
                tamper_active = !tamper_active;
                printk("EV,%d,TAMPER,%d\n", i, tamper_active);
                fake_sensor_set_tamper(tamper_active);
                break;
#endif
            default:
                break;
        }
        k_msleep(5);
    }

#ifdef CONFIG_THREAD_ANALYZER
    thread_analyzer_print();
#endif
    printk("ORACLE_DONE\n");
    return 0;
}

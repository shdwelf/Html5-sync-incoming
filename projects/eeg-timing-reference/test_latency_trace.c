#include "latency_trace.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static void test_happy_path(void) {
    lt_trace_t trace;
    uint64_t delta = 0u;

    lt_trace_init(&trace, 17u, "PTP-1");
    assert(trace.sequence == 17u);
    assert(strcmp(trace.clock_domain, "PTP-1") == 0);
    assert(lt_trace_mark(&trace, LT_STAGE_DRDY, 1000u) == LT_OK);
    assert(lt_trace_mark(&trace, LT_STAGE_SPI_DMA_DONE, 1075u) == LT_OK);
    assert(lt_trace_mark(&trace, LT_STAGE_PROCESS_DONE, 1180u) == LT_OK);
    assert(lt_trace_mark(&trace, LT_STAGE_LOCAL_EVENT, 1220u) == LT_OK);
    assert(lt_trace_mark(&trace, LT_STAGE_OBSERVER_TX, 1260u) == LT_OK);
    assert(lt_trace_delta_ns(&trace, LT_STAGE_DRDY, LT_STAGE_LOCAL_EVENT, &delta) == LT_OK);
    assert(delta == 220u);
}

static void test_order_and_monotonicity(void) {
    lt_trace_t trace;

    lt_trace_init(&trace, 2u, "PTP-1");
    assert(lt_trace_mark(&trace, LT_STAGE_SPI_DMA_DONE, 10u) == LT_ERR_STAGE_ORDER);
    assert(lt_trace_mark(&trace, LT_STAGE_DRDY, 100u) == LT_OK);
    assert(lt_trace_mark(&trace, LT_STAGE_DRDY, 101u) == LT_ERR_DUPLICATE_STAGE);
    assert(lt_trace_mark(&trace, LT_STAGE_SPI_DMA_DONE, 99u) == LT_ERR_TIME_ORDER);
    assert(lt_trace_mark(&trace, LT_STAGE_SPI_DMA_DONE, 110u) == LT_OK);
    assert(lt_trace_mark(&trace, LT_STAGE_PROCESS_DONE, 120u) == LT_OK);
}

static void test_missing_and_clock_health(void) {
    lt_trace_t trace;
    lt_clock_health_t good = { true, 80u };
    lt_clock_health_t stale = { false, 0u };
    uint64_t ignored = 0u;

    lt_trace_init(&trace, 3u, NULL);
    assert(lt_trace_delta_ns(&trace, LT_STAGE_DRDY, LT_STAGE_PROCESS_DONE, &ignored) == LT_ERR_MISSING_STAGE);
    assert(lt_clock_is_usable(&good, 80u));
    assert(!lt_clock_is_usable(&good, 79u));
    assert(!lt_clock_is_usable(&stale, 0u));
    assert(!lt_clock_is_usable(NULL, 0u));
}

int main(void) {
    test_happy_path();
    test_order_and_monotonicity();
    test_missing_and_clock_health();
    puts("latency_trace tests: PASS");
    return 0;
}

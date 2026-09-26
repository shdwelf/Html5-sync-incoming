# Portable host test for the latency instrumentation core. The target is placed
# in /tmp so a test run cannot create a distributable firmware artifact.
CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -pedantic -O2
BIN := /tmp/eeg-timing-reference-test

.PHONY: test clean

test: $(BIN)
	$(BIN)

$(BIN): latency_trace.c latency_trace.h test_latency_trace.c
	$(CC) $(CFLAGS) -I. latency_trace.c test_latency_trace.c -o $(BIN)

clean:
	rm -f $(BIN)

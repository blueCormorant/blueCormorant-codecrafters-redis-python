#!/bin/bash

echo "Running Unit Tests"

echo "PING Command"
echo $(nc -C -w 1 localhost 6379 < unit_tests/ping.txt)

echo "PING Array Command"
echo $(nc -C -w 1 localhost 6379 < unit_tests/ping_array.txt)

echo "PING Array Multi Command"
echo $(nc -C -w 1 localhost 6379 < unit_tests/multi_ping_array.txt)

echo "ECHO Command \"Hey\""
echo $(nc -C -w 1 localhost 6379 < unit_tests/echo1.txt)

echo "ECHO Command \"Hello\""
echo $(nc -C -w 1 localhost 6379 < unit_tests/echo2.txt)

echo "Set Command \"apple px 1000\""
echo $(nc -C -w 1 localhost 6379 < unit_tests/set_apple_px.txt)

echo "Set Command \"bannana px 9000\""
echo $(nc -C -w 1 localhost 6379 < unit_tests/set_bannana_px.txt)

echo "Get Command \"apple\""
echo $(nc -C -w 1 localhost 6379 < unit_tests/get_apple.txt)

echo "Get Command \"bannana\""
echo $(nc -C -w 1 localhost 6379 < unit_tests/get_bannana.txt)


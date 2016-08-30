#!/usr/bin/env bash
touch nohup.out
nohup python ./run.py & tail -f nohup.out

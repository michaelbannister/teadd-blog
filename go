#!/bin/bash
set -e

ansible-playbook provision.yml
ansible-playbook -i gce.py configure.yml

#!/bin/bash
cd "${0%/*}"
source "../config.sh"
curl https://members.hacman.org.uk/query2.php?key=${MEMBERS_API_KEY} -o "members.csv"

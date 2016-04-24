#!/bin/bash

TIMESTAMP=$(date -u "+%Y-%m-%dT%H%M%S")

cat > make-backup.sh <<-END
  mkdir -p backups
  cd backups
  sudo /opt/bitnami/ctlscript.sh stop
  sudo tar -pczf "$TIMESTAMP.tar.gz" /opt/bitnami
  sudo /opt/bitnami/ctlscript.sh start
END

chmod a+x make-backup.sh

mkdir -p backups

gcloud compute copy-files make-backup.sh ghost-2-vm:~
gcloud compute ssh ghost-2-vm --command ./make-backup.sh
gcloud compute copy-files "ghost-2-vm:~/backups/$TIMESTAMP.tar.gz" backups

rm make-backup.sh

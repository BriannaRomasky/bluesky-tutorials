# Monitor supervisord if it was started already

# jupyter-repo2docker supports running a script at container
# start time (i.e. ENTRYPOINT). If supervisord has been run, this could be used
# to monitor its status and no action will be required by the user.

DIR=`dirname "\$0"`

supervisorctl -c $DIR/supervisord.conf status

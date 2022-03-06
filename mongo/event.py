from blinker import signal

requirement_added = signal('requirement_added')
submission_completed = signal('submission_completed')
comment_created = signal('comment_created')
reply_created = signal('reply_created')
comment_liked = signal('comment_be_liked')
comment_unliked = signal('comment_unliked')
task_time_changed = signal('task_time_changed')

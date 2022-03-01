from blinker import signal

task_due_extended = signal('task_due_extended')
requirement_added = signal('requirement_added')
submission_completed = signal('submission_completed')
comment_created = signal('comment_created')
reply_created = signal('reply_created')
comment_liked = signal('comment_be_liked')
comment_unliked = signal('comment_unliked')
task_time_change = signal('task_time_change')

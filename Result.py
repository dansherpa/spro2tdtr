class Result:
  def __init__(self, bib, start_micros, start, finish_micros, finish, net_raw, net_time):
    self.bib = bib
    self.start_micros = start_micros
    self.start = start
    self.finish_micros = finish_micros
    self.finish = finish
    self.net_raw = net_raw
    self.net_time = net_time

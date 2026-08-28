# A threshold is moved by a listen, not by a distribution

The pause threshold and floor stay at 0.7 s and 0.3 s. The quiet still playing under the
bar is a smooth ramp with no step in it, so no number taken from that distribution is
anything but invented. The evidence that can move the bar is someone listening to a cut
made at it, and until that exists the defaults hold.

## Context

06 chose 0.7 s and 0.3 s, and until the quiet was found under the words rather than
between them the threshold only ever applied to dead air *between* attempts, where the
material runs 1.5–7 s. It had never once fired inside a line. So the number was carrying
a job it had never been tested on.

Measured after that change, the regions under the bar and still playing inside a line are
16 worth 9.4 s on `sequence.mp4` and 14 worth 8.0 s on `Sequence 07.mp4`, every one of
them between 0.40 s and 0.69 s. There is no gap anywhere in that range to put a
threshold in — it is a ramp, and picking a point on it is the objection 07 and 08 have
each already sustained by name.

The other half is what the range is. 0.4–0.7 s between words inside a sentence is
breathing. 06 chose a floor of 0.3 s precisely because a read with the pauses taken out
sounds machine-gunned, so cutting a 0.45 s region down to 0.30 s buys 0.15 s at the
price of an edit point.

## Consequences

The first real evidence about whether 0.7 s is the right bar inside a line is the
acceptance listen on ticket 10. Moving the number afterwards is a deliberate second act,
taken on what someone heard, rather than a guess made now.

If that listen finds the cut breathless, the first thing to hand back is the nine regions
between 0.70 s and 0.80 s across both recordings, and `--pause-threshold-seconds 0.8`
hands back exactly those without inventing a new number.

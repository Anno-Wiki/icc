On Emphasis
===========

Emphasis in the DOM is actually a complicated thing.

First let us note that we store emphasis in the line merely as markdown style
underscores, as in the raw text '_this is emphasized_'.

Since each line is represented as an independent entity in the DOM (and in the
database), we sometimes find emphasis traversing database/DOM entities.

Now, since you can have emphasis traversing several lines, as in the following
example:

_Tomorrow and tomorrow and tomorrow,
Creeps in this petty pace from day to day
To the last syllable of recorded time
And all our yesterdays have lighted fools
The way to dusty death—Out, out, brief candle!
Life's but a walking shadow, a poor player
Who struts and frets his hour upon the stage
And then is heard no more. It is a tale
Told by an idiot, full of sound and fury,
Signifying nothing—_

In which the emphasis on the entire body of the text is marked merely by an
introductory underscore before 'Tomorrow' and a concluding underscore after
'nothing—', we run into a problem in the DOM if we render the underscores into
html naively, namely, this:

    <div><em>Tomorrow and tomorrow and tomorrow,</div>
    <div>Creeps in this petty pace from day to day</div>
    <div>To the last syllable of recorded time</div>
    <div>And all our yesterdays have lighted fools</div>
    <div>The way to dusty death—Out, out, brief candle!</div>
    <div>Life's but a walking shadow, a poor player</div>
    <div>Who struts and frets his hour upon the stage</div>
    <div>And then is heard no more. It is a tale</div>
    <div>Told by an idiot, full of sound and fury,</div>
    <div>Signifying nothing—_</em></div>

As you can see, the opening and closing `<em>` tags span across multiple
elements in the DOM. This _breaks_ the DOM, which requires us to get clever.

As such there is a simple integer column on the line table called 'em_id'. It is
translated into an enum based on a tuple declared at the top of the models file
for content. The enums are named:

    0   nem     no emphasis
    1   oem     open emphasis
    2   em      emphasis
    3   cem     close emphasis

The correspond to the following situations:

1. `nem`: There is no emphasis on the line, leave it alone. This includes lines in
   which emphasis is opened and closed in the same line.
2. `oem`: There is an opening emphasis tag in the current line, as in the
   following: `_Tomorrow and tomorrow and tomorrow`. In that case, we need to
   close the emphasis with an `</em>` tag at the end.
3. `em`: There is ongoing emphasis between lines in this case, as in the body of
   the speech from Macbeth quoted above. In that case we both prepend and close
   the line with `<em>` and `</em>` tags.
4. `cem`: There is a closing emphasis tag in the current line, as in the end of
   the speech, and so we need to prepend the line with an open `<em>` tag.

Currently I believe my processor even works in one extreme edge case:

_This line is openly emphasized but it
Continues onto the second line only to be closed_ and then _re-opened
Continuing on to the next line only to end_.

In this case, the emphasis would be opened by the first line (`oem`), the middle
line would be marked `em`, and the last line would be marked `cem` resulting in
the following:

    <div><em>This line is openly emphasized but it</em></div>
    <div><em>Continues onto the second line only to be closed</em> and then <em>re-opened</em></div>
    <div><em>Continuing on to the next line only to end</em>.</div>

Which works perfectly.

Currently, this is all processed by a function called `underscores_to_ems`
defined in the read route. It is not used in any other routes because the system
requires you to annotate the plaintext.

This may eventually change.

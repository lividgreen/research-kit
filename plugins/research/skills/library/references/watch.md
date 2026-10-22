# The watch

The watch answers one question: what is new since it last looked.
It is a check and not a schedule: it keeps what it has seen and no clock, no interval and no date of its last run, so a run right after a run reports nothing and writes no file, and when it runs is the business of whoever runs it.
A watch is one of four looks: the newest works citing a card, asked of OpenAlex's citing filter and of the OpenCitations index where OpenAlex does not answer; the works OpenAlex relates to a card; the newest arXiv entries answering a query in arXiv's own syntax; the repositories answering a query in GitHub's search syntax, which is how a new tool or software library is watched for.
Each look takes in a bounded window of the newest works, one or two calls a watch — one more per work named where the OpenCitations index answers in place of OpenAlex, since it names a citing work by identifier alone — with no key.
A work no run has seen is new; it is proposed as a candidate unless a card or a candidate already goes by one of its identifiers, and its identifiers are recorded as seen either way.
At a watch's first run a work dated before the watch's `since` is recorded as seen and not proposed, so a new watch does not propose a work's whole past; `since` is the day the watch was added unless a date is given to look back.
When an interface does not answer, the run says so and exits as failed, and nothing is recorded for that watch.
A candidate is not a card: it carries its identifiers, a title, why it surfaced and the date.
Making one a card is `library resolve` or `library register` by hand, after which it leaves the list by itself; setting one aside is `library candidates --exclude` with a reason, after which no watch proposes it again; what a candidate means for the project is written wherever the project keeps such things, by hand.
The watches with their seen identifiers and the candidates are two tracked files beside the cards, written by the tool alone, so that a reinstalled machine does not report everything again.

# Bloblang for Expanso mappings

Bloblang is the mapping language in `mapping` processors, in `generate`
mappings, in `args_mapping`, and inside `${! ... }` interpolations in string
fields. Every construct below appears in a file that passes
`expanso-edge validate` v2.1.21. Full reference:
<https://docs.expanso.io/guides/bloblang/methods>.

## Core

```coffee
root = this                          # copy the whole message
root.received_at = now()             # add a field
root = this.without("password")      # drop fields
root = this.merge({"kind": "error"}) # merge one object (one argument)
root = deleted()                     # drop the message
root.raw = content().string()        # raw bytes as a string
meta trace_id = uuid_v4()            # set metadata
root.topic = @mqtt_topic             # read metadata (also meta("name"))
root.seq = count("my_counter")       # monotonically increasing counter
root.salt = env("IP_SALT").or("")    # node environment, with a fallback
```

## Variables: `let` is a statement

```coffee
let parts = this.full_name.split(",")
root.last_name = $parts.index(0).trim()
```

Read a variable back with a `$` prefix: `$parts`, never bare `parts` (a bare
name is a path into the message, so `line.trim()` reads a field called `line`).

`let` and `meta` are **statements**. They cannot appear inside an
`if`/`else`/`match` that is used as an expression. This is the most common
error in the catalog:

```coffee
# REJECTED: `let` inside an expression-position if body
root.x = if this.a != null {
  let y = this.a.number()
  $y * 2
} else { 0 }

# ACCEPTED: hoist the statement
let y = this.a.number().catch(0)
root.x = if this.a != null { $y * 2 } else { 0 }
```

## Conditionals

```coffee
root = if ["critical", "high"].contains(this.severity) { this } else { deleted() }

root.status = match this.status_code {
  "A" => "active"
  "I" => "inactive"
  _ => throw("unknown status code " + this.status_code)
}
```

`throw("...")` marks the message errored; route it with `errored()` and read
the reason with `error()` (see the output `switch` in `components.md`).

## Arrays

```coffee
root.first = this.items.index(0)          # not this.items[0] with an expression
root.big = this.nums.filter(n -> n > 10)  # ONE argument: a lambda
root.doubled = this.nums.map_each(n -> n * 2)
root.n = this.items.length()
root = if $items.type() == "array" { $items } else { [$items] }
```

## Strings, numbers, hashing

```coffee
root.email = this.email.trim().lowercase()
root.label = "[%s] %s".format(this.severity.uppercase(), this.message)
root.domain = this.email.split("@").index(1)
root.matches = this.value.re_find_all("a.")          # one argument
let m = content().string().re_find_object("^(?P<ip>\\S+) (?P<rest>.*)$")
root.cents = this.balance_cents.number().int64()
root.temp_c = ((this.temp_f - 32) * 5 / 9).round()
root.ip_hash = this.ip.hash("sha256", env("IP_SALT").or(""))
root.key = this.guid.hash("sha256").encode("hex")
root.pretty = this.sample.format_json()
```

## Timestamps

```coffee
# parse with strptime directives, format with a Go layout
root.day = this.signup.ts_strptime("%m/%d/%Y").ts_format("2006-01-02", "UTC")
root.at = (1767225600 + $n * 86400).ts_format("2006-01-02T15:04:05Z", "UTC")
# try one layout, then another
let pd = this.pubDate
root.published_at = $pd.ts_strptime(
  "%a, %d %b %Y %H:%M:%S %z"
).catch($pd.ts_strptime(
  "%a, %d %b %Y %H:%M:%S %Z"
)).ts_format("2006-01-02T15:04:05Z07:00", "UTC")
```

Inside `.catch(...)`, `this` is not the original message; bind what you need to
a variable first, as above.

Not available at v2.1.21 (rejected as unrecognised): `ts_add`,
`format_timestamp_iso8601`, `parse_timestamp_iso8601`. A duration string such
as `"2h"` passed where a timestamp is expected fails with
`parsing time "2h" as "2006-01-02T15:04:05..."`.

## Interpolation in string fields

```yaml
key: '${! json("id") }'
value: '${! json("minute") } ${! json("path") }'
url: "https://api.example.com/items/${! this.id }"
```

`${VAR}` and `${VAR:default}` (no `!`) substitute a node environment variable
when the config loads. A numeric field such as a rate-limit `count` or
`batching.count` must be a number, not an env interpolation string.

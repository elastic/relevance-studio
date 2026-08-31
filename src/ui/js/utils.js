/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { EuiText } from '@elastic/eui'

const utils = {}

/**
 * Creates a generic toast for responses from the axios client.
 */
utils.toastClientResponse = (response) => {
  console.debug(`Toast: [response]`, response)
  return {
    title: response.statusText,
    text: (
      <EuiText size='xs' color='subdued'>
        {JSON.stringify(response.data, null, 2)}
      </EuiText>
    )
  }
}

/**
 * Creates a generic toast for errors from the axios client.
 */
utils.toastClientError = (error) => {
  console.debug(`Toast: [Error]`, error)
  return {
    title: error.statusText,
    color: 'danger',
    text: (
      <EuiText size='xs' color='subdued'>
        {JSON.stringify(error, null, 2)}
      </EuiText>
    )
  }
}

/**
 * Creates a generic toast for successfully creating, updating, or deleting a doc.
 */
utils.toastDocCreateUpdateDelete = (action, docType, _id) => {
  console.debug(`Toast: ${action} ${docType} ${_id}`)
  let title
  if (action == 'create')
    title = `Created ${docType}`
  else if (action == 'update')
    title = `Updated ${docType}`
  else if (action == 'delete')
    title = `Deleted ${docType}`
  else if (action == 'queue')
    title = `Queued ${docType}`
  return {
    title: title,
    color: 'success',
    iconType: 'check',
    text: (
      <EuiText size='xs'>
        <EuiText color='subdued' size='xs'>
          <small>{_id}</small>
        </EuiText>
      </EuiText>
    )
  }
}

/**
 * After getting a list of hits (e.g. displays, scenarios, strategies),
 * convert them into an array of docs containing their _source and _id.
 */
utils.hitsToDocs = (response) => {

  // If response has hits, it's from POST _search
  if (response.data.hits)
    return response.data.hits.hits.map(doc => ({ ...doc._source, _id: doc._id }))

  // Otherwise, it's from GET /_doc
  return [{ ...response.data._source, _id: response.data._id }]
}

/**
 * After getting aggregations, convert them into aggs keyed by doc _id.
 */
utils.hitsToAggs = (response) => {
  const aggs = {}
  response.data.aggregations?.counts?.buckets?.forEach(agg => {
    const subAggs = {};
    for (const [key, value] of Object.entries(agg)) {
      if (key === 'key' || key === 'doc_count')
        continue
      subAggs[key] = value?.doc_count || 0;
    }
    aggs[agg.key] = {
      ...aggs[agg.key] || {},
      ...subAggs
    }
  })
  return aggs
}

/**
 * Store an array of docs by their doc _id.
 * Typically used after utils.hitsToDocs.
 */
utils.toMap = (items) =>
  items.reduce((acc, item) => {
    acc[item._id] = item
    return acc
  }, {})

/**
 * Find the value of a nested field in an object using a path with dot noation.
 */
utils.getNestedValue = (obj, path) => {
  if (!obj || !path)
    return undefined;
  const pathArray = path.split('.')
  let current = obj;
  for (const key of pathArray)
    if (current && typeof current === 'object' && current.hasOwnProperty(key))
      current = current[key]
    else
      return undefined
  return current
}

/**
 * Calculate the average of an array of numbers
 */
utils.average = (arr) => {
  const avg = arr.reduce((a, b) => a + b, 0) / arr.length
  return isNaN(avg) ? 0 : avg
}

/**
 * Convert a timestamp to "time ago" format
 */
utils.timeAgo = (timestamp) => {
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })
  const seconds = Math.floor((Date.now() - new Date(timestamp)) / 1000)
  const ranges = {
    year: 31536000,
    month: 2592000,
    week: 604800,
    day: 86400,
    hour: 3600,
    minute: 60,
    second: 1
  }
  for (const [unit, secondsInUnit] of Object.entries(ranges)) {
    const delta = Math.floor(seconds / secondsInUnit)
    if (Math.abs(delta) >= 1)
      return rtf.format(-delta, unit) // negative for "ago"
  }
  return 'just now'
}

/**
 * Given a number of milliseconds, return a human readable format of that time.
 */
utils.formatDuration = (ms) => {
  const s = Math.floor(ms / 1000);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;

  return (
    (h ? `${h}h` : '') +
    (m ? `${m}m` : '') +
    (sec || (!h && !m) ? `${sec}s` : '')
  )
}

utils.jsonStringifySortedKeys = (obj, replacer = null, space = 2) => {
  const sortKeys = (value) => {
    if (Array.isArray(value))
      return value.map(sortKeys)
    if (value && typeof value === 'object' && value.constructor === Object) {
      return Object.keys(value).sort().reduce((acc, key) => {
        acc[key] = sortKeys(value[key]);
        return acc
      }, {})
    } else {
      return value
    }
  }
  return JSON.stringify(sortKeys(obj), replacer, space)
}

utils.jsonStringifySortedKeysWithTripleQuotes = (obj, replacer = null, space = 2) => {
  const serialize = (value, currentIndent = 0) => {
    const currentIndentStr = ' '.repeat(currentIndent)
    const nextIndent = currentIndent + space
    const nextIndentStr = ' '.repeat(nextIndent)
    if (value === null)
      return 'null'
    if (typeof value === 'undefined')
      return 'undefined'
    if (typeof value === 'boolean' || typeof value === 'number')
      return String(value)
    if (typeof value === 'string') {
      if (value.includes('\n'))
        return `"""\n${value.split('\\n').join('')}\n"""`
      else
        return utils.jsonStringifySortedKeys(value, replacer, space)
    }
    if (Array.isArray(value)) {
      if (value.length === 0)
        return '[]'
      const items = value.map(item => nextIndentStr + serialize(item, nextIndent))
      return '[\n' + items.join(',\n') + '\n' + currentIndentStr + ']'
    }
    if (typeof value === 'object') {
      const keys = Object.keys(value).sort()
      if (keys.length === 0)
        return '{}'
      const items = keys.map(key => {
        const serializedKey = utils.jsonStringifySortedKeys(key, replacer, space)
        const serializedValue = serialize(value[key], nextIndent)
        return `${nextIndentStr}${serializedKey}: ${serializedValue}`
      })
      return '{\n' + items.join(',\n') + '\n' + currentIndentStr + '}'
    }
    return utils.jsonStringifySortedKeys(value, replacer, space) // fallback
  }
  return serialize(obj, 0)
}

/**
 * Validate and format JSON with Mustache.
 * 
 * types:
 *   "string"          -> placeholder: "__MUSTACHE_var__"
 *   "number"          -> placeholder: 0
 *   "boolean"         -> placeholder: false
 *   "null"            -> placeholder: null
 *   "array"           -> placeholder: []
 *   "array-string"    -> placeholder: ["__MUSTACHE_var__"]
 *   "object"          -> placeholder: {}
 *
 * Any var not in types -> defaults to null (safe JSON).
 */

const MUSTACHE_RE = /\{\{\s*([#/>^&!]*)\s*([a-zA-Z0-9._-]+)\s*([^}]*)\}\}/g;

const makePlaceholder = (varName, kind = "null") => {
  switch (kind) {
    case "string": return JSON.stringify(`__MUSTACHE_${varName}__`);
    case "number": return "0";
    case "boolean": return "false";
    case "array": return "[]";
    case "array-string": return `["__MUSTACHE_${varName}__"]`;
    case "object": return "{}";
    case "null":
    default: return "null";
  }
}

const sanitizeJsonWithMustache = (src, types = {}) => {
  // Ignore sections/partials/etc by treating any non-empty sigil as plain placeholder
  return src.replace(MUSTACHE_RE, (_, sigil, name) => {
    // If this is a section/partial/inverted/etc (sigil present), default to null
    if (sigil && sigil !== "") return makePlaceholder(name, types[name] || "null");
    return makePlaceholder(name, types[name] || "null");
  });
}

const restoreMustache = (formatted, original, types = {}) => {
  // Recreate the exact placeholders we produced in sanitize()
  // Then replace them back to raw {{ name }} (without quotes if placeholder was non-string)
  const produced = [];
  original.replace(MUSTACHE_RE, (_, sigil, name) => {
    const kind = types[name] || "null";
    switch (kind) {
      case "string": {
        const quoted = JSON.stringify(`__MUSTACHE_${name}__`);
        produced.push([quoted, `{{ ${name} }}`]); // remove quotes entirely
        break;
      }
      case "array-string": {
        const arr = `["__MUSTACHE_${name}__"]`;
        produced.push([arr, `{{ ${name} }}`]); // drop whole token (array) back to mustache
        break;
      }
      case "number":
      case "boolean":
      case "array":
      case "object":
      case "null":
      default: {
        const token = makePlaceholder(name, kind);
        produced.push([token, `{{ ${name} }}`]);
      }
    }
  });

  // Apply replacements carefully, from longest to shortest token to avoid overlaps
  produced.sort((a, b) => b[0].length - a[0].length);

  // Replace all occurrences
  let out = formatted
  for (const [placeholder, raw] of produced)
    out = out.split(placeholder).join(raw)
  return out
}

/**
 * Lints + formats. Throws if the JSON (after sanitization) is invalid.
 * Returns { formatted, errors: [] } on success.
 */
utils.formatJsonWithMustache = (source, types = {}) => {
  const sanitized = sanitizeJsonWithMustache(source, types)
  let parsed
  try {
    parsed = JSON.parse(sanitized)
  } catch (err) {
    // Bubble a helpful error that points into the sanitized string
    err.message = `JSON-with-Mustache validation failed: ${err.message}`
    throw err
  }
  const pretty = JSON.stringify(parsed, null, 2)
  const restored = restoreMustache(pretty, source, types)
  return restored
}

/**
 * Given an Elasticsearch field type, return its corresponding EuiIcon type and color.
 */
utils.iconTypeFromFieldType = (fieldType) => {
  var iconColor = 'success'
  var iconType = 'tokenField'
  switch (fieldType) {
    case 'binary':
      iconColor = 'danger'
      iconType = 'tokenBinary'
      break
    case 'boolean':
      iconColor = 'primary'
      iconType = 'tokenBoolean'
      break
    case 'completion':
    case 'search_as_you_type':
      iconColor = 'primary'
      iconType = 'tokenCompletionSuggester'
      break
    case 'date':
    case 'date_nanos':
      iconColor = 'warning'
      iconType = 'tokenDate'
      break
    case 'geo_point':
    case 'geo_shape':
    case 'point':
    case 'shape':
      iconColor = 'warning'
      iconType = 'tokenGeo'
      break
    case 'ip':
      iconColor = 'danger'
      iconType = 'tokenIP'
      break
    case 'join':
      iconColor = 'warning'
      iconType = 'tokenJoin'
      break
    case 'constant_keyword':
    case 'keyword':
    case 'wildcard':
      iconColor = 'primary'
      iconType = 'tokenKeyword'
      break
    case 'nested':
      iconColor = 'danger'
      iconType = 'tokenNested'
      break
    case 'byte':
    case 'double':
    case 'float':
    case 'half_float':
    case 'integer':
    case 'long':
    case 'scaled_float':
    case 'short':
    case 'unsigned_long':
      iconColor = 'success'
      iconType = 'tokenNumber'
      break
    case 'object':
      iconColor = 'danger'
      iconType = 'tokenObject'
      break
    case 'date_range':
    case 'double_rage':
    case 'float_range':
    case 'integer_range':
    case 'ip_range':
    case 'long_range':
      iconColor = 'danger'
      iconType = 'tokenRange'
      break
    case 'rank_feature':
      iconColor = 'warning'
      iconType = 'tokenRankFeature'
      break
    case 'rank_features':
    case 'rank_vectors':
      iconColor = 'success'
      iconType = 'tokenRankFeatures'
      break
    case 'semantic_text':
      iconColor = 'success'
      iconType = 'tokenSemanticText'
      break
    case 'text':
      iconColor = 'primary'
      iconType = 'tokenText'
      break
    case 'dense_vector':
      iconColor = 'warning'
      iconType = 'tokenVectorDense'
      break
    case 'sparse_vector':
      iconColor = 'success'
      iconType = 'tokenVectorSparse'
      break
    default:
      break
  }
  return { color: iconColor, type: iconType }
}

/**
 * Split an index pattern on commas, which workspaces and displays allow.
 */
utils.splitIndexPatterns = (indexPattern) =>
  (indexPattern || '').split(',').map((part) => part.trim()).filter(Boolean)

/**
 * Convert an index pattern into a regex that matches index names, treating
 * '*' as a wildcard and every other character literally.
 */
utils.indexPatternToRegex = (indexPattern) => {
  const escaped = indexPattern.replace(/[.+?^${}()|[\]\\]/g, '\\$&')
  return new RegExp(`^${escaped.replace(/\*/g, '.*')}$`)
}

/**
 * Given displays, return a matcher per display: the regexes of the index
 * patterns it includes, and the regexes of the index patterns it excludes.
 * An index pattern can name several indices with commas, and can exclude one
 * of them by prefixing it with '-', as Elasticsearch does.
 *
 * This is a list rather than a map keyed by index pattern, so that two
 * displays naming the same index pattern don't silently overwrite each other.
 */
utils.makeDisplayMatchers = (displays) => {
  const matchers = []
  displays?.forEach((display) => {
    const includes = []
    const excludes = []
    utils.splitIndexPatterns(display.index_pattern).forEach((part) => {
      const isExcluded = part.startsWith('-')
      const indexPattern = isExcluded ? part.slice(1) : part
      if (!indexPattern)
        return
      const matcher = { indexPattern, regex: utils.indexPatternToRegex(indexPattern) }
      isExcluded ? excludes.push(matcher) : includes.push(matcher)
    })
    if (includes.length)
      matchers.push({ display: display, includes: includes, excludes: excludes })
  })
  return matchers
}

/**
 * Given displays, return the deduplicated list of their fields, which is used
 * to filter the _source of documents in search requests.
 */
utils.makeSourceFilters = (displays) => {
  const sourceFilters = {}
  displays?.forEach((display) => {
    display.fields?.forEach((field) => {
      sourceFilters[field] = true
    })
  })
  return Object.keys(sourceFilters)
}

/**
 * How strongly a matcher matches an index: by the index name itself, which is
 * more direct than by one of its aliases, and then by the length of the index
 * pattern, which is the same "most specific wins" heuristic used elsewhere.
 * Returns null if the matcher doesn't match the index at all.
 */
const matchStrength = (matcher, index, aliases) => {
  let strength = null
  matcher.includes.forEach(({ indexPattern, regex }) => {
    let rank = 0
    if (regex.test(index))
      rank = 2
    else if (aliases.some((alias) => regex.test(alias)))
      rank = 1
    if (!rank)
      return
    if (
      !strength ||
      rank > strength.rank ||
      (rank === strength.rank && indexPattern.length > strength.length)
    )
      strength = { rank: rank, length: indexPattern.length }
  })
  return strength
}

/**
 * Given an index name, find the display whose index pattern matches it with
 * the most specificity.
 *
 * Documents report the concrete index they live in, but a display can name an
 * alias of that index instead. So consider the aliases of the index, too,
 * while preferring a display that names the index itself. aliasMap maps index
 * names to their aliases, as returned by api.content_aliases().
 */
utils.resolveIndexToDisplay = (matchers, index, aliasMap) => {
  if (!index)
    return null
  const aliasesOfIndex = aliasMap?.[index]
  const aliases = Array.isArray(aliasesOfIndex) ? aliasesOfIndex : []
  const names = [index, ...aliases]
  let best = null
  matchers?.forEach((matcher) => {
    if (matcher.excludes.some(({ regex }) => names.some((name) => regex.test(name))))
      return
    const strength = matchStrength(matcher, index, aliases)
    if (!strength)
      return
    if (
      !best ||
      strength.rank > best.strength.rank ||
      (strength.rank === best.strength.rank && strength.length > best.strength.length)
    )
      best = { display: matcher.display, strength: strength }
  })
  return best ? best.display : null
}

export default utils
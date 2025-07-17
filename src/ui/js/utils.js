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

export default utils
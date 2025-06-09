import React from 'react'
import {
  EuiText,
} from '@elastic/eui'

const utils = {}

/**
 * Creates a generic toast for responses from the axios client.
 */
utils.toastClientResponse = (response) => {
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
utils.average = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length

/**
 * Given an Elasticsearch field type, return its corresponding EuiIcon type and color.
 */
utils.iconTypeFromFieldType = (fieldType) => {
  var iconColor = 'success'
  var iconType = 'tokenField'
  switch(fieldType) {
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
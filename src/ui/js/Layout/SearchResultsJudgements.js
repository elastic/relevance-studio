/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  EuiFlexGrid,
  EuiFlexItem,
} from '@elastic/eui'
import {
  JudgementCard,
} from '.'

const SearchResultsJudgements = ({
  resolveIndexToDisplay,
  workspace,
  scenario,
  results,
  resultsPerRow,
  showScore,
}) => {

  const cards = []
  results.forEach((result) => {
    cards.push(
      <JudgementCard
        key={`${result.doc._index}~${result.doc._id}`}
        _id={result._id}
        doc={result.doc}
        workspace={workspace}
        scenario={scenario}
        rating={result.rating}
        createdBy={result['@meta']?.created_by}
        updatedBy={result['@meta']?.updated_by}
        updatedVia={result['@meta']?.updated_via}
        template={resolveIndexToDisplay(result.doc._index)?.template}
        showScore={showScore}
      />
    )
  })

  return (
    <EuiFlexGrid columns={parseInt(resultsPerRow)} direction='row' gutterSize='m'>
      {cards.map((card, i) => {
        return (
          <EuiFlexItem key={i}>
            {card}
          </EuiFlexItem>
        )
      })}
    </EuiFlexGrid>
  )
}

export default SearchResultsJudgements
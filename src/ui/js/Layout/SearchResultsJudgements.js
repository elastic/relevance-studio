import {
  EuiFlexGrid,
  EuiFlexItem,
} from '@elastic/eui'
import {
  JudgementCard,
} from '.'

const SearchResultsJudgements = ({
  displays,
  indexPatternRegexes,
  project,
  scenario,
  results,
  resultsPerRow,
  showScore,
}) => {

  /**
   * Given an index name, find the display whose index pattern matches it
   * with the most specificity.
   */
  const resolveIndexToDisplay = (index) => {
    const matches = []
    for (const indexPattern in indexPatternRegexes)
      if (indexPatternRegexes[indexPattern].test(index))
        matches.push(indexPattern)
    if (matches.length === 0)
      return null
    const bestMatch = matches.reduce((mostSpecific, current) =>
      current.length > mostSpecific.length ? current : mostSpecific
    )
    return displays[bestMatch]
  }

  const cards = []
  results.forEach((result) => {
    cards.push(
      <JudgementCard
        key={`${result.doc._id}~${result.doc._id}`}
        _id={result._id}
        doc={result.doc}
        project={project}
        scenario={scenario}
        rating={result.rating}
        author={result['@author']}
        timestamp={result['@timestamp']}
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
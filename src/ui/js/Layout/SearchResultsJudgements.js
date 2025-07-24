import {
  EuiFlexGrid,
  EuiFlexItem,
} from '@elastic/eui'
import {
  JudgementCard,
} from '.'

const SearchResultsJudgements = ({
  indexPatternMap,
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
    for (const indexPattern in indexPatternMap)
      if (indexPatternMap[indexPattern].regex.test(index))
        matches.push(indexPattern)
    if (matches.length === 0)
      return null
    const bestMatch = matches.reduce((mostSpecific, current) =>
      current.length > mostSpecific.length ? current : mostSpecific
    )
    return indexPatternMap[bestMatch].display
  }

  const cards = []
  results.forEach((result) => {
    cards.push(
      <JudgementCard
        key={`${result.doc._index}~${result.doc._id}`}
        _id={result._id}
        doc={result.doc}
        project={project}
        scenario={scenario}
        rating={result.rating}
        createdBy={result['@meta']?.created_by}
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
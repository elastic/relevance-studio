/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  EuiCode,
  EuiCodeBlock,
  EuiLink,
  EuiFlyout,
  EuiFlyoutBody,
  EuiFlyoutHeader,
  EuiText,
  EuiTitle
} from '@elastic/eui'

const FlyoutHelp = ({ onClose }) => {

  const codeBlock = `{
  "retriever": {
    "standard": {
      "query": {
        "multi_match": {
          "query": "{{ text }}"
        }
      }
    }
  }
}`

  return (
    <EuiFlyout onClose={onClose}>
      <EuiFlyoutHeader hasBorder>
        <EuiTitle size='m'>
          <h2>How to use this editor</h2>
        </EuiTitle>
      </EuiFlyoutHeader>
      <EuiFlyoutBody>
        <EuiText>
          <h4>
            What is a strategy?
          </h4>
          <p>
            A <b>strategy</b> is a <EuiLink href='https://www.elastic.co/docs/solutions/search/retrievers-overview' target='_blank'>retriever</EuiLink> or <EuiLink href='https://www.elastic.co/docs/explore-analyze/query-filter/languages/querydsl' target='_blank'>query</EuiLink> that you want to test in your search relevance benchmark runs. It becomes the contents of the <EuiCode>"source"</EuiCode> field of a <EuiLink href='https://www.elastic.co/docs/solutions/search/search-templates' target='_blank'>search template</EuiLink> in the <EuiLink href='https://www.elastic.co/guide/en/elasticsearch/reference/8.18/search-rank-eval.html' target='_blank'>Ranking Evaluation API</EuiLink>.
          </p>
          <h4>
            How do I let my strategy accept variable inputs?
          </h4>
          <p>
            Use <EuiLink href='https://www.elastic.co/docs/solutions/search/search-templates#create-search-template' target='_blank'>double curly braces</EuiLink> to define <b>params</b>, which indicate where your strategy will accept inputs. If the input will be a string, be sure to surround the variable with double quotes. Remember to surround a param with double quotes (<EuiCode>"</EuiCode>) if it expects a string value.
          </p>
          <p>
            In the example strategy below, the <EuiCode>{'{{ text }}'}</EuiCode> param is where a search scenario would pass the value from its own <EuiCode>text</EuiCode> param.
          </p>
          <p>
          <EuiCodeBlock language='json'>
            {codeBlock}
          </EuiCodeBlock>
          </p>
          <h4>
            How do I tune a value with a hyperparameter?
          </h4>
          <p>
            A <b>hyperparameter</b> is a value of your strategy that a benchmark can search, such as a boost. Reference it with the <EuiCode>hp.</EuiCode> prefix, for example <EuiCode>{'{{hp.boost}}'}</EuiCode>. The prefix keeps hyperparameters apart from scenario params. Then define it in the <b>Hyperparameters</b> section under the editor with a type, a promoted value (the value the strategy uses today) and the valid testable values (the values a benchmark may test).
          </p>
          <p>
            To reference a value that needs JSON formatting, such as a boolean or a number inside a string, use <EuiCode>{'{{#toJson}}hp.name{{/toJson}}'}</EuiCode>.
          </p>
          <p>
            The Search tab tests the draft on one scenario. Its hyperparameter inputs start at the promoted values, and you can change them to explore. The Benchmark tab compares the draft against the saved strategy across scenarios, and can test hyperparameter values with a holdout. Apply a winning variant to the draft, then save to keep it.
          </p>
        </EuiText>
      </EuiFlyoutBody>
    </EuiFlyout>
  )
}

export default FlyoutHelp
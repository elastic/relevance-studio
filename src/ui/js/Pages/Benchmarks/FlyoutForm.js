import React, { useEffect, useState } from 'react'
import {
  EuiAccordion,
  EuiBadge,
  EuiButton,
  EuiButtonEmpty,
  EuiButtonGroup,
  EuiCallOut,
  EuiComboBox,
  EuiForm,
  EuiFormRow,
  EuiFieldNumber,
  EuiFieldText,
  EuiIcon,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFlyout,
  EuiFlyoutFooter,
  EuiInMemoryTable,
  EuiNotificationBadge,
  EuiPanel,
  EuiSpacer,
  EuiSuperSelect,
  EuiSwitch,
  EuiTabbedContent,
  EuiText,
  EuiTextArea,
  EuiTitle,
} from '@elastic/eui'
import { useProjectContext } from '../../Contexts/ProjectContext'
import api from '../../api'

const FlyoutForm = ({ action, doc, onClose }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const {
    project,
    isProjectReady,
    loadAssets,
    isProcessingBenchmark,
    scenarios,
    strategies,
    createBenchmark,
    updateBenchmark
  } = useProjectContext()

  /**
   * Load (or reload) any needed assets when project is ready.
   */
  useEffect(() => {
    if (isProjectReady)
      loadAssets({ scenarios: true, strategies: true })
  }, [project?._id])

  ////  State  /////////////////////////////////////////////////////////////////

  const [form, setForm] = useState({
    name: '',
    description: '',
    tags: [],
    metrics: ['ndcg', 'precision', 'recall'],
    k: 10,
    strategies_mode: 'all',
    strategies_ids: [],
    strategies_tags: [],
    scenarios_mode: 'all',
    scenarios_ids: [],
    scenarios_tags: [],
    scenarios_sample_size: 1000,
    scenarios_sample_seed: ''
  })
  const [formBlurs, setFormBlurs] = useState({
    name: false,
    metrics: false,
    k: false
  })
  const [isLoadingCandidates, setIsLoadingCandidates] = useState(false)
  const [limitScenariosByTags, setLimitScenariosByTags] = useState(false)
  const [limitStrategiesByTags, setLimitStrategiesByTags] = useState(false)
  const [scenariosTagsOptions, setScenariosTagsOptions] = useState([])
  const [scenariosCandidates, setScenariosCandidates] = useState([])
  const [strategiesCandidates, setStrategiesCandidates] = useState([])
  const [strategiesTagsOptions, setStrategiesTagsOptions] = useState([])

  ////  Effects  ///////////////////////////////////////////////////////////////

  /**
   * Load strategies tags
   */
  useEffect(() => {
    if (!strategies)
      return
    const tags = {}
    for (const _id in strategies)
      (strategies[_id].tags || []).forEach((tag) => tags[tag] = true)
    const options = []
    for (const tag in tags) {
      options.push({
        color: 'primary',
        key: tag,
        label: tag,
        prepend: <EuiIcon size='s' type='tag' />
      })
    }
    options.sort((a, b) => a.label.localeCompare(b.label))
    setStrategiesTagsOptions(options)
  }, [strategies])

  /**
   * Load scenarios tags
   */
  useEffect(() => {
    if (!scenarios)
      return
    const tags = {}
    for (const _id in scenarios)
      (scenarios[_id].tags || []).forEach((tag) => tags[tag] = true)
    const options = []
    for (const tag in tags) {
      options.push({
        key: tag,
        label: tag,
        prepend: <EuiIcon size='s' type='tag' />
      })
    }
    options.sort((a, b) => a.label.localeCompare(b.label))
    setScenariosTagsOptions(options)
  }, [scenarios])

  /**
   * Preview candidate pool
   */
  useEffect(() => {
    if (!strategies || !scenarios)
      return
    const previewCandidatePool = async () => {
      setIsLoadingCandidates(true)
      try {
        const body = {
          strategies: {
            _ids: form.strategies_ids,
            tags: form.strategies_tags
          },
          scenarios: {
            _ids: form.scenarios_ids,
            tags: form.scenarios_tags,
          },
          scenarios_sample_size: form.scenarios_sample_size
        }
        if (form.scenarios_sample_seed != '')
          body.scenarios_sample_seed = form.scenarios_sample_seed
        const response = await api.benchmarks_make_candidate_pool(project._id, body)
        setStrategiesCandidates(response.data?.strategies || [])
        setScenariosCandidates(response.data?.scenarios || [])
      } finally {
        setIsLoadingCandidates(false)
      }
    }
    previewCandidatePool()
  }, [
    form.strategies_mode,
    form.strategies_ids, 
    form.strategies_tags,
    form.scenarios_mode,
    form.scenarios_ids,
    form.scenarios_tags,
    form.scenarios_sample_size,
    form.scenarios_sample_seed,
  ])

  // Populate form with doc if updating
  useEffect(() => {
    if (action != 'update')
      return
    setForm({
      name: doc.name,
      description: doc.description,
      tags: doc.tags || [],
      metrics: doc.task?.metrics || [],
      k: doc.task?.k || 10,
      strategies_mode: (doc.task?.strategies?._ids || []) ? 'specific' : 'all',
      strategies_ids: doc.task?.strategies?._ids || [],
      strategies_tags: doc.task?.strategies?.tags || [],
      scenarios_mode: (doc.task?.scenarios?._ids || []) ? 'specific' : 'all',
      scenarios_ids: doc.task?.scenarios?._ids || [],
      scenarios_tags: doc.task?.scenarios?.tags || [],
      scenarios_sample_size: doc.task?.scenarios_sample_size || 1000,
      scenarios_sample_seed: doc.task?.scenarios_sample_seed || '',
    })
  }, [doc])

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onSubmit = async (e) => {
    e.preventDefault();
    const newDoc = doc ? { ...doc } : {}
    newDoc.name = form.name.trim()
    const _description = form.description.trim()
    if (_description != '')
      newDoc.description = _description
    const _tags = form.tags.map(t => t.trim()).filter(t => t != '').sort()
    if (_tags.length)
      newDoc.tags = _tags
    newDoc.task = {
      metrics: form.metrics,
      k: form.k
    }
    const _strategies = {}
    if (form.strategies_ids.length)
      _strategies._ids = form.strategies_ids
    if (form.strategies_tags.length)
      _strategies.tags = form.strategies_tags
    if (Object.keys(_strategies).length)
      newDoc.task.strategies = _strategies
    const _scenarios = {}
    if (form.scenarios_ids.length)
      _scenarios._ids = form.scenarios_ids
    if (form.scenarios_tags.length)
      _scenarioss.tags = form.scenarios_tags
    if (form.scenarios_sample_size)
      _scenarios.sample_size = form.scenarios_sample_size
    if (form.scenarios_sample_seed !== '')
      _scenarios.sample_seed = form.scenarios_sample_seed
    if (Object.keys(_scenarios).length)
      newDoc.task.scenarios = _scenarios
    if (action == 'create') {
      await createBenchmark(newDoc)
    } else if (action == 'update') {
      await updateBenchmark(doc._id, newDoc)
    }
    onClose()
  }

  ////  Form validation  ///////////////////////////////////////////////////////

  const isInvalidName = () => !form.name?.trim()
  const isInvalidMetrics = () => !form.metrics.length
  const isInvalidK = () => form.k <= 0
  const isInvalidForm = () => {
    return isInvalidName() || isInvalidMetrics() || isInvalidK()
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderFormName = () => {
    return (
      <EuiFieldText
        aria-label='Benchmark name'
        compressed
        fullWidth
        isInvalid={formBlurs.name && isInvalidName()}
        onBlur={(e) => setFormBlurs(prev => ({ ...prev, name: true }))}
        onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
        placeholder='Name'
        value={form.name}
      />
    )
  }

  const renderFormDescription = () => {
    return (
      <EuiTextArea
        aria-label='Description (optional)'
        compressed
        fullWidth
        onChange={(e) => setForm(prev => ({ ...prev, description: e.target.value }))}
        placeholder='What are goals of this benchmark?'
        value={form.description}
      />
    )
  }

  const renderFormTags = () => {
    return (
      <EuiComboBox
        aria-label='Tags'
        compressed
        fullWidth
        noSuggestions
        onChange={(options) => {
          const tags = []
          options.forEach((option) => tags.push(option.key))
          setForm(prev => ({ ...prev, ['tags']: tags }))
        }}
        onCreateOption={(tag) => {
          const tags = form.tags?.concat(tag)
          setForm(prev => ({ ...prev, ['tags']: tags }))
        }}
        placeholder='Tags'
        selectedOptions={form.tags?.map((tag) => ({
          key: tag,
          label: tag,
          prepend: <EuiIcon size='s' type='tag' />
        }))}
      />
    )
  }

  const renderFormMetrics = () => {
    return (
      <EuiFlexGroup gutterSize='s' responsive={false}>
        <EuiFlexItem grow={6}>
          <EuiButtonGroup
            buttonSize='compressed'
            color={formBlurs.metrics && isInvalidMetrics() ? 'text' : 'primary'}
            disabled={action == 'update'}
            isFullWidth
            idToSelectedMap={{
              'ndcg': form.metrics.includes('ndcg'),
              'precision': form.metrics.includes('precision'),
              'recall': form.metrics.includes('recall'),
            }}
            isInvalid={formBlurs.metrics && isInvalidMetrics()}
            legend='Metric'
            onBlur={() => {
              setFormBlurs(prev => ({ ...prev, metrics: true }))
            }}
            onChange={(id) => {
              setForm(prev => {
                return {
                  ...prev,
                  metrics: prev.metrics.includes(id)
                    ? prev.metrics.filter(v => v !== id)
                    : [...prev.metrics, id]
                }
              })
            }}
            options={[
              {
                id: 'ndcg',
                label: (<EuiText size='xs'>NDCG</EuiText>),
              },
              {
                id: 'precision',
                label: (<EuiText size='xs'>Recall</EuiText>),
              },
              {
                id: 'recall',
                label: (<EuiText size='xs'>Precision</EuiText>),
              },
            ]}
            type='multi'
          />
        </EuiFlexItem>
        <EuiFlexItem grow={4}>
          <EuiFieldNumber
            compressed
            disabled={action == 'update'}
            isInvalid={formBlurs.k && isInvalidK()}
            min={1}
            onBlur={() => {
              setFormBlurs(prev => ({ ...prev, k: true }))
            }}
            onChange={(e) => {
              setForm(prev => ({ ...prev, k: e.target.value }))
            }}
            prepend='k'
            step={1}
            value={form.k}
          />
        </EuiFlexItem>
      </EuiFlexGroup>
    )
  }

  const renderFormStrategies = () => {
    return (<>
      <EuiSuperSelect
        compressed
        fullWidth
        readOnly // TODO: Implement choices
        onChange={(value) => setForm(prev => ({ ...prev, strategies_mode: value }))}
        options={[
          {
            value: 'all',
            inputDisplay: (
              <EuiText size='s'>
                <EuiIcon
                  color='primary'
                  type='sparkles'
                  style={{ marginRight: '10px' }}
                />
                Use all compatible strategies at runtime
              </EuiText>
            ),
          },
          {
            value: 'specific',
            inputDisplay: (
              <EuiText size='s'>
                <EuiIcon
                  color='primary'
                  type='editorChecklist'
                  style={{ marginRight: '10px' }}
                />
                Use specific strategies
              </EuiText>
            ),
          },
        ]}
        valueOfSelected={form.strategies_mode}
      />
    </>)
  }

  const renderFormScenarios = () => {
    return (<>
      <EuiSuperSelect
        compressed
        fullWidth
        readOnly // TODO: Implement choices
        onChange={(value) => setForm(prev => ({ ...prev, scenarios_mode: value }))}
        options={[
          {
            value: 'all',
            inputDisplay: (
              <EuiText size='s'>
                <EuiIcon
                  color='primary'
                  type='sparkles'
                  style={{ marginRight: '10px' }}
                />
                Use all compatible scenarios at runtime
              </EuiText>
            ),
          },
          {
            value: 'specific',
            inputDisplay: (
              <EuiText size='s'>
                <EuiIcon
                  color='primary'
                  type='editorChecklist'
                  style={{ marginRight: '10px' }}
                />
                Use specific scenarios
              </EuiText>
            ),
          },
        ]}
        valueOfSelected={form.scenarios_mode}
      />
    </>)
  }

  const renderFormStrategiesTags = () => {
    return (
      <EuiFlexGroup alignItems='center' gutterSize='none' style={{ height: '32px' }}>
        <EuiFlexItem grow={false}>
          <EuiSwitch
            checked={limitStrategiesByTags}
            compressed
            onChange={() => {
              if (limitStrategiesByTags) {
                setForm(prev => ({ ...prev, ['strategies_tags']: [] }))
                setLimitStrategiesByTags(false)
              } else {
                setLimitStrategiesByTags(true)
              }
            }}
          />
        </EuiFlexItem>
        <EuiFlexItem grow>
          {!limitStrategiesByTags &&
            <EuiText
              color='subdued'
              onClick={() => {
                if (limitStrategiesByTags) {
                  setForm(prev => ({ ...prev, ['strategies_tags']: [] }))
                  setLimitStrategiesByTags(false)
                } else {
                  setLimitStrategiesByTags(true)
                }
              }}
              size='s'
              style={{ paddingLeft: '8px' }}
            >
              Limit by tags
            </EuiText>
          }
          {!!limitStrategiesByTags &&
            <EuiComboBox
              aria-label='Strategy tags'
              autoFocus
              compressed
              fullWidth
              onChange={(options) => {
                const tags = []
                options.forEach((option) => tags.push(option.key))
                setForm(prev => ({ ...prev, ['strategies_tags']: tags }))
              }}
              onCreateOption={(tag) => {
                const tags = form.strategies_tags?.concat(tag)
                setForm(prev => ({ ...prev, ['strategies_tags']: tags }))
              }}
              options={strategiesTagsOptions}
              placeholder='Limit by tags'
              selectedOptions={form.strategies_tags?.map((tag) => ({
                key: tag,
                label: tag,
                prepend: <EuiIcon size='s' type='tag' />
              }))}
            />
          }
        </EuiFlexItem>
      </EuiFlexGroup>
    )
  }

  const renderFormScenariosTags = () => {
    return (
      <EuiFlexGroup alignItems='center' gutterSize='none' style={{ height: '32px' }}>
        <EuiFlexItem grow={false}>
          <EuiSwitch
            checked={limitScenariosByTags}
            compressed
            onChange={() => {
              if (limitScenariosByTags) {
                setForm(prev => ({ ...prev, ['scenarios_tags']: [] }))
                setLimitScenariosByTags(false)
              } else {
                setLimitScenariosByTags(true)
              }
            }}
          />
        </EuiFlexItem>
        <EuiFlexItem grow>
          {!limitScenariosByTags &&
            <EuiText
              color='subdued'
              onClick={() => {
                if (limitScenariosByTags) {
                  setForm(prev => ({ ...prev, ['scenarios_tags']: [] }))
                  setLimitScenariosByTags(false)
                } else {
                  setLimitScenariosByTags(true)
                }
              }}
              size='s'
              style={{ paddingLeft: '8px' }}
            >
              Limit by tags
            </EuiText>
          }
          {!!limitScenariosByTags &&
            <EuiComboBox
              aria-label='Scenario tags'
              autoFocus
              compressed
              fullWidth
              onChange={(options) => {
                const tags = []
                options.forEach((option) => tags.push(option.key))
                setForm(prev => ({ ...prev, ['scenarios_tags']: tags }))
              }}
              onCreateOption={(tag) => {
                const tags = form.scenarios_tags?.concat(tag)
                setForm(prev => ({ ...prev, ['scenarios_tags']: tags }))
              }}
              options={scenariosTagsOptions}
              placeholder='Limit by tags'
              selectedOptions={form.scenarios_tags?.map((tag) => ({
                key: tag,
                label: tag,
                prepend: <EuiIcon size='s' type='tag' />
              }))}
            />
          }
        </EuiFlexItem>
      </EuiFlexGroup>
    )
  }

  const renderFormStrategiesCandidates = () => {
    const docs = []
    strategiesCandidates.forEach((_id) => docs.push(strategies[_id]))
    return (
      <>
        <EuiSpacer size='s' />
        <EuiCallOut
          iconType='pin'
          size='s'
          title='These are the current strategies that match your task definition.'
        >
          <p>
            At runtime, the benchmark will evaluate all strategies that share the same params as your chosen scenarios, and that match your chosen strategy tags.
          </p>
        </EuiCallOut>
        <EuiSpacer size='s' />
        <EuiInMemoryTable
          columns={[
            {
              field: 'name',
              name: 'Strategy',
              sortable: true,
              truncateText: true,
              render: (name, doc) => <EuiText size='xs'>{doc.name}</EuiText>
            },
            {
              field: 'tags',
              name: 'Tags',
              width: '100px',
              render: (name, doc) => {
                const tags = []
                for (var i in doc.tags)
                  tags.push(
                    <EuiBadge color='hollow' key={doc.tags[i]}>
                      <small>{doc.tags[i]}</small>
                    </EuiBadge>
                  )
                return tags
              },
            },
          ]}
          items={docs}
          pagination={true}
          responsiveBreakpoint={false}
          sorting={{
            sort: {
              field: 'name',
              direction: 'asc',
            }
          }}
          tableLayout='custom'
        >
        </EuiInMemoryTable>
      </>
    )
  }

  const renderFormScenariosCandidates = () => {
    const docs = []
    scenariosCandidates.forEach((_id) => docs.push(scenarios[_id]))
    return (
      <>
        <EuiSpacer size='s' />
        <EuiCallOut
          iconType='pin'
          size='s'
          title='These are the current scenarios that match your task definition.'
        >
          <p>
            At runtime, the benchmark will evaluate scenarios that share the same params as your chosen strategies, and that match your chosen scenario tags. It will select a maximum random sample of {form.sample_size} scenarios, stratified by tags and judgement ratings.
          </p>
        </EuiCallOut>
        <EuiSpacer size='s' />
        <EuiInMemoryTable
          columns={[
            {
              field: 'name',
              name: 'Scenario',
              sortable: true,
              truncateText: true,
              render: (name, doc) => <EuiText size='xs'>{doc.name}</EuiText>
            },
            {
              field: 'tags',
              name: 'Tags',
              width: '100px',
              render: (name, doc) => {
                const tags = []
                for (var i in doc.tags)
                  tags.push(
                    <EuiBadge color='hollow' key={doc.tags[i]}>
                      <small>{doc.tags[i]}</small>
                    </EuiBadge>
                  )
                return tags
              },
            },
          ]}
          items={docs}
          pagination={true}
          responsiveBreakpoint={false}
          sorting={{
            sort: {
              field: 'name',
              direction: 'asc',
            }
          }}
          tableLayout='custom'
        >
        </EuiInMemoryTable>
      </>
    )
  }

  return (
    <EuiForm>
      <EuiFlyout hideCloseButton onClose={onClose} ownFocus size='l'>
        <EuiFlexGroup gutterSize='none'>

          {/* Inputs */}
          <EuiFlexItem grow={5}>
            <EuiPanel color='transparent' paddingSize='l'>
              <EuiTitle>
                <EuiText>
                  <h2>{action == 'create' ? 'Create' : 'Edit'} benchmark</h2>
                </EuiText>
              </EuiTitle>
              <EuiSpacer size='l' />

              {/* Name */}
              <EuiFormRow fullWidth label='Name'>
                {renderFormName()}
              </EuiFormRow>
              <EuiSpacer size='l' />

              {/* Metrics */}
              <EuiFormRow
                fullWidth
                label={(() => {
                  if (formBlurs.metrics && isInvalidMetrics())
                    return (<>
                      Metrics
                      <EuiIcon
                        color='danger'
                        size='s'
                        style={{
                          marginBottom: '2px',
                          marginLeft: '10px',
                          marginRight: '8px'
                        }}
                        type='warning'
                      />
                      <EuiText
                        color='subdued'
                        size='xs'
                        style={{ display: 'inline', fontWeight: 'normal' }}
                      >
                        Choose at least one metric
                      </EuiText>
                    </>)
                  return 'Metrics'
                })()}
              >
                {renderFormMetrics()}
              </EuiFormRow>
              <EuiSpacer size='l' />

              {/* Strategies */}
              <EuiFormRow fullWidth label='Strategies'>
                <>
                  {renderFormStrategies()}
                  <EuiSpacer size='xs' />
                  {renderFormStrategiesTags()}
                </>
              </EuiFormRow>
              <EuiSpacer size='l' />

              {/* Scenarios */}
              <EuiFormRow fullWidth label='Scenarios'>
                <>
                  {renderFormScenarios()}
                  <EuiSpacer size='xs' />
                  {renderFormScenariosTags()}
                </>
              </EuiFormRow>
              <EuiSpacer size='l' />

              {/* Description */}
              <EuiFormRow fullWidth label='Description'>
                <>
                  {renderFormDescription()}
                  <EuiSpacer size='xs' />
                  {renderFormTags()}
                </>
              </EuiFormRow>
              <EuiSpacer size='m' />

              {/* Advanced settings */}
              <EuiAccordion
                buttonContent='Show advanced settings'
                id={'advanced-settings'}
              >
                <EuiSpacer size='m' />

                {/* Random sampling */}
                <EuiFormRow label='Random sampling'>
                  <>
                    <EuiFieldNumber
                      compressed
                      min={1}
                      onChange={(e) => setForm(prev => ({ ...prev, scenarios_sample_size: e.target.value }))}
                      prepend={
                        <small style={{ width: '80px' }}>
                          Maximum size
                        </small>
                      }
                      step={1}
                      value={form.scenarios_sample_size || 0}
                    />
                    <EuiSpacer size='xs' />
                    <EuiFieldText
                      compressed
                      onChange={(e) => setForm(prev => ({ ...prev, scenarios_sample_seed: e.target.value }))}
                      prepend={
                        <small style={{ width: '80px' }}>
                          Seed
                        </small>
                      }
                      value={form.scenarios_sample_seed || ''}
                    />
                  </>
                </EuiFormRow>
              </EuiAccordion>
            </EuiPanel>

            {/* Footer */}
            <EuiFlyoutFooter>
              <EuiFlexGroup justifyContent='spaceBetween'>
                <EuiFlexItem grow={false}>
                  <EuiButtonEmpty
                    disabled={isProcessingBenchmark}
                    flush='left'
                    iconType='cross'
                    onClick={onClose}
                  >
                    Cancel
                  </EuiButtonEmpty>
                </EuiFlexItem>
                <EuiFlexItem grow={false}>
                  <EuiButton
                    color='primary'
                    disabled={isProcessingBenchmark || isInvalidForm()}
                    fill
                    onClick={onSubmit}
                    type='submit'
                  >
                    {action == 'create' ? 'Create' : 'Save'}
                  </EuiButton>
                </EuiFlexItem>
              </EuiFlexGroup>
            </EuiFlyoutFooter>
          </EuiFlexItem>

          {/* Preview */}
          <EuiFlexItem grow={5} style={{ borderLeft: '1px solid rgb(211, 218, 230)' }}>
            <EuiPanel color='transparent' paddingSize='l'>
              <EuiTitle>
                <EuiText>
                  <h2>Preview</h2>
                </EuiText>
              </EuiTitle>
              <EuiSpacer size='l' />
              <EuiTabbedContent
                tabs={[
                  {
                    id: 'strategies',
                    name: (
                      <div>
                        Strategies <EuiNotificationBadge color='subdued' style={{ marginLeft: '8px' }}><small>{strategiesCandidates.length || 0}</small></EuiNotificationBadge>
                      </div>
                    ),
                    content: renderFormStrategiesCandidates()
                  },
                  {
                    id: 'scenarios',
                    name: (
                      <div>
                        Scenarios <EuiNotificationBadge color='subdued' style={{ marginLeft: '8px' }}><small>{scenariosCandidates.length || 0}</small></EuiNotificationBadge>
                      </div>
                    ),
                    content: renderFormScenariosCandidates()
                  }
                ]}
                initialSelectedTab={'strategies'}
                onTabClick={(tab) => {
                  console.log('clicked tab', tab);
                }}
              />
            </EuiPanel>
          </EuiFlexItem>

        </EuiFlexGroup>
      </EuiFlyout>
    </EuiForm>
  )
}

export default FlyoutForm
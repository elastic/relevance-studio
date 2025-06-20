import React, { useEffect, useState } from 'react'
import {
  EuiButton,
  EuiButtonEmpty,
  EuiButtonGroup,
  EuiComboBox,
  EuiForm,
  EuiFormRow,
  EuiFieldNumber,
  EuiIcon,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFlyout,
  EuiFlyoutBody,
  EuiFlyoutHeader,
  EuiFlyoutFooter,
  EuiInlineEditTitle,
  EuiPanel,
  EuiSpacer,
  EuiSuperSelect,
  EuiSwitch,
  EuiText,
  EuiTextArea,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import api from '../../api'
import utils from '../../utils'

const FlyoutForm = ({ action, doc, onClose, onCreated, onUpdated }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [form, setForm] = useState({
    name: '',
    description: '',
    tags: [],
    metrics: ['ndcg', 'precision', 'recall'],
    k: 10,
    strategies: 'all',
    scenarios: 'all'
  })
  const [formBlurs, setFormBlurs] = useState({
    name: false,
    metrics: false,
    k: false
  })
  const [isLoading, setIsLoading] = useState(false)

  ////  Effects  ///////////////////////////////////////////////////////////////

  // Populate form with doc if updating
  useEffect(() => {
    if (action != 'update')
      return
    setForm({
      name: doc.name,
      description: doc.description,
      tags: doc.tags || [],
      metrics: doc.config?.metrics || [],
      k: doc.config?.k || 10
    })
  }, [doc])

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onSubmit = (e) => {
    e.preventDefault();
    const newDoc = doc ? { ...doc } : {}
    newDoc.name = form.name.trim()
    newDoc.description = form.description.trim()
    newDoc.tags = form.tags.map(t => t.trim()).filter(t => t != '').sort()
    if (action == 'create')
      return onSubmitCreate(newDoc)
    if (action == 'update')
      return onSubmitUpdate(newDoc)
  }

  const onSubmitCreate = (newDoc) => {
    (async () => {

      // Submit API request
      let response
      try {
        setIsLoading(true)
        response = await api.projects_create(newDoc)
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to create project' }))
      } finally {
        setIsLoading(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Created project',
        color: 'success',
        iconType: 'check',
        text: (
          <EuiText size='xs'>
            <b>{newDoc.name}</b><br />
            <EuiText color='subdued' size='xs'>
              <small>{response.data._id}</small>
            </EuiText>
          </EuiText>
        )
      })
      newDoc._id = response.data._id
      onCreated(newDoc)
      onClose()
    })()
  }

  const onSubmitUpdate = (newDoc) => {
    (async () => {

      // Submit API request
      let response
      try {
        setIsLoading(true)
        response = await api.projects_update(doc._id, newDoc)
      } catch (err) {
        return addToast(api.errorToast(err, { title: 'Failed to create project' }))
      } finally {
        setIsLoading(false)
      }

      // Handle API response
      if (response.status < 200 && response.status > 299)
        return addToast(utils.toastClientResponse(response))
      addToast({
        title: 'Updated project',
        color: 'success',
        iconType: 'check',
        text: (
          <EuiText size='xs'>
            <b>{newDoc.name}</b><br />
            <EuiText color='subdued' size='xs'>
              <small>{response.data._id}</small>
            </EuiText>
          </EuiText>
        )
      })
      onUpdated(newDoc)
      onClose()
    })()
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
      <EuiInlineEditTitle
        heading='h2'
        inputAriaLabel='Benchmark name'
        isInvalid={formBlurs.name && isInvalidName()}
        placeholder='Set benchmark name'
        onBlur={(e) => setFormBlurs(prev => ({ ...prev, name: true }))}
        onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
        value={form.name}
      />
    )
  }

  const renderFormDescription = () => {
    return (
      <EuiTextArea
        aria-label='Description (optional)'
        compressed
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
        selectedOptions={form.tags?.map((tag) => ({ key: tag, label: tag }))}
      />
    )
  }

  const renderFormMetrics = () => {
    return (
      <EuiFlexGroup gutterSize='s' responsive={false}>
        <EuiFlexItem grow={6}>
          <EuiButtonGroup
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
            prepend='@'
            append='k'
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
        fullWidth
        onChange={(value) => setForm(prev => ({ ...prev, strategies: value }))}
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
                Use all compatible strategies
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
        valueOfSelected={form.strategies}
      />
      {/*<EuiSwitch
        compressed
        label='Limit by tags'
      />*/}
    </>)
  }

  const renderFormScenarios = () => {
    return (<>
      <EuiSuperSelect
        fullWidth
        onChange={(value) => setForm(prev => ({ ...prev, scenarios: value }))}
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
                Use all compatible scenarios
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
        valueOfSelected={form.scenarios}
      />
    </>)
  }

  return (
    <EuiForm>
      <EuiFlyout hideCloseButton onClose={onClose} ownFocus size='l'>
        <EuiFlyoutHeader hasBorder>
          {renderFormName()}
        </EuiFlyoutHeader>
        <EuiFlyoutBody>

          {/* Description and tags */}
          <EuiPanel color='subdued' paddingSize='m'>
            <EuiFormRow label='Description'>
              {renderFormDescription()}
            </EuiFormRow>
            <EuiSpacer size='xs' />
            <EuiFormRow>
              {renderFormTags()}
            </EuiFormRow>
          </EuiPanel>

          <EuiSpacer size='m' />

          {/* Metrics, strategies, and scenarios */}
          <EuiPanel paddingSize='m'>
            <EuiFormRow
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
            <EuiSpacer margin='s' />
            <EuiFlexGroup gutterSize='m'>
              <EuiFlexItem grow={5}>
                <EuiFormRow fullWidth label='Strategies'>
                  {renderFormStrategies()}
                </EuiFormRow>
              </EuiFlexItem>
              <EuiFlexItem grow={5}>
                <EuiFormRow fullWidth label='Scenarios'>
                  {renderFormScenarios()}
                </EuiFormRow>
              </EuiFlexItem>
            </EuiFlexGroup>
          </EuiPanel>
        </EuiFlyoutBody>
        <EuiFlyoutFooter>
          <EuiFlexGroup justifyContent='spaceBetween'>
            <EuiFlexItem grow={false}>
              <EuiButtonEmpty
                disabled={isLoading}
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
                disabled={isLoading || isInvalidForm()}
                fill
                onClick={onSubmit}
                type='submit'
              >
                {action == 'create' ? 'Create' : 'Save'}
              </EuiButton>
            </EuiFlexItem>
          </EuiFlexGroup>
        </EuiFlyoutFooter>
      </EuiFlyout>
    </EuiForm>
  )
}

export default FlyoutForm
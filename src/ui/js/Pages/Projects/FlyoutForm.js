import { useEffect, useState } from 'react'
import {
  EuiButton,
  EuiButtonEmpty,
  EuiButtonIcon,
  EuiForm,
  EuiFormControlLayoutDelimited,
  EuiFormRow,
  EuiFieldNumber,
  EuiFieldText,
  EuiLink,
  EuiFlexGroup,
  EuiFlexItem,
  EuiFlyout,
  EuiFlyoutBody,
  EuiFlyoutHeader,
  EuiFlyoutFooter,
  EuiInlineEditTitle,
  EuiSpacer,
  EuiToolTip,
} from '@elastic/eui'
import { useAppContext } from '../../Contexts/AppContext'
import api from '../../api'
import utils from '../../utils'

const FlyoutForm = ({
    action,
    doc,
    isProcessing,
    onClose,
    onSuccess,
    setIsProcessing
  }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [form, setForm] = useState({
    name: '',
    index_pattern: '',
    params: [{ name: 'text' }],
    rating_scale: {
      min: 0,
      max: 4
    }
  })
  const [formBlurs, setFormBlurs] = useState({
    name: false,
    index_pattern: false,
    rating_scale_min: false,
    rating_scale_max: false
  })

  ////  Effects  ///////////////////////////////////////////////////////////////

  // Populate form with doc if updating
  useEffect(() => {
    if (action != 'update')
      return
    setForm({
      name: doc.name,
      index_pattern: doc.index_pattern,
      params: (doc.params || []).map(p => { return { name: p } }),
      rating_scale: {
        min: doc.rating_scale?.min || 0,
        max: doc.rating_scale?.max || 4
      }
    })
  }, [doc])

  ////  Event handlers  ////////////////////////////////////////////////////////

  const onSubmit = async (e) => {
    // prevent browser from reloading page if called from a form submission
    e?.preventDefault();
    const newDoc = doc ? { ...doc } : {}
    newDoc.name = form.name.trim()
    newDoc.index_pattern = form.index_pattern.trim()
    newDoc.params = form.params.map(p => p.name.trim()).filter(p => p != '').sort()
    newDoc.rating_scale = {
      min: form.rating_scale.min,
      max: form.rating_scale.max
    }

    // Submit API request
    let response
    try {
      setIsProcessing(true)
      if (action == 'create')
        response = await api.projects_create(newDoc)
      else
        response = await api.projects_update(doc._id, newDoc)
    } catch (e) {
      return addToast(api.errorToast(e, { title: `Failed to {action} project` }))
    } finally {
      setIsProcessing(false)
    }
    if (response.status > 299)
      return addToast(utils.toastClientResponse(response))
    addToast(utils.toastDocCreateUpdateDelete(action, 'project', response.data._id, newDoc))
    if (onSuccess)
      onSuccess()
    if (onClose)
      onClose()
  }

  ////  Form validation  ///////////////////////////////////////////////////////

  const isInvalidName = () => !form.name?.trim()
  const isInvalidIndexPattern = () => !form.index_pattern?.trim()
  const isInvalidRatingScaleMin = () => form.rating_scale.min >= form.rating_scale.max
  const isInvalidRatingScaleMax = () => form.rating_scale.max <= form.rating_scale.min
  const isInvalidParams = () => {
    if (!form.params.length)
      return true
    for (const i in form.params)
      if (form.params[i].name?.trim())
        return false
    return true
  }
  const isInvalidForm = () => {
    return isInvalidName() || isInvalidIndexPattern() || isInvalidRatingScaleMin() || isInvalidRatingScaleMax() || isInvalidParams()
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const renderFormName = () => {
    return (
      <EuiInlineEditTitle
        heading='h2'
        inputAriaLabel='Project name'
        isInvalid={formBlurs.name && isInvalidName()}
        placeholder='Set project name'
        onBlur={(e) => setFormBlurs(prev => ({ ...prev, name: true }))}
        onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
        value={form.name}
      />
    )
  }

  const renderFormRatingScale = () => {
    return (<>
      <EuiFormControlLayoutDelimited
        prepend='Min'
        append='Max'
        isDisabled={action == 'update'}
        startControl={
          <EuiFieldNumber
            controlOnly
            disabled={action == 'update'}
            isInvalid={formBlurs.rating_scale_min && isInvalidRatingScaleMin()}
            min={0}
            onBlur={() => {
              setFormBlurs(prev => ({ ...prev, rating_scale_max: true }))
            }}
            onChange={(e) => {
              setForm(prev => ({
                ...prev, rating_scale: {
                  ...prev.rating_scale, min: e.target.value
                }
              }))
            }}
            step={1}
            value={form.rating_scale.min}
          />
        }
        endControl={
          <EuiFieldNumber
            controlOnly
            disabled={action == 'update'}
            isInvalid={formBlurs.rating_scale_max && isInvalidRatingScaleMax()}
            min={1}
            onBlur={() => {
              setFormBlurs(prev => ({ ...prev, rating_scale_min: true }))
            }}
            onChange={(e) => {
              setForm(prev => ({
                ...prev, rating_scale: {
                  ...prev.rating_scale, max: e.target.value
                }
              }))
            }}
            step={1}
            value={form.rating_scale.max}
          />
        }
      />
    </>)
  }

  const renderFormIndexPattern = () => {
    return (
      <EuiFieldText
        aria-label='Set index name'
        isInvalid={formBlurs.index_pattern && isInvalidIndexPattern()}
        onBlur={() => setFormBlurs(prev => ({ ...prev, index_pattern: true }))}
        onChange={(e) => setForm(prev => ({ ...prev, index_pattern: e.target.value }))}
        placeholder='Set index pattern'
        value={form.index_pattern}
      />
    )
  }

  const renderFormParams = () => {
    const rows = []
    form.params.forEach((param, i) => {
      const row = (
        <div key={i}>
          <EuiFlexGroup gutterSize='xs' responsive={false}>
            <EuiFlexItem grow>
              <EuiFieldText
                aria-label='Set param name'
                onChange={(e) => {
                  setForm(prev => {
                    const newParams = [...prev.params]
                    newParams[i] = {
                      ...newParams[i],
                      name: e.target.value
                    }
                    return { ...prev, params: newParams }
                  })
                }}
                placeholder='name'
                value={param.name}
              />
            </EuiFlexItem>
            <EuiFlexItem grow={false}>
              <EuiToolTip content='Remove param'>
                <EuiButtonIcon
                  aria-label='Remove param'
                  color='danger'
                  display='empty'
                  iconType='cross'
                  onClick={() => {
                    setForm(prev => ({
                      ...prev,
                      params: prev.params.filter((_, idx) => idx !== i)
                    }))
                  }}
                  size='m'
                />
              </EuiToolTip>
            </EuiFlexItem>
          </EuiFlexGroup>
          <EuiSpacer size='xs' />
        </div>
      )
      rows.push(row)
    })
    return (<>
      {rows}
      <EuiButton
        color={form.params.length ? 'text' : 'danger'}
        iconType='plusInCircle'
        onClick={() => {
          setForm(prev => ({
            ...prev, params: [
              ...prev.params, {
                name: ''
              }
            ]
          }))
        }}
        size='s'
      >
        <small>add param</small>
      </EuiButton>
    </>)
  }

  return (
    <EuiForm>
      <EuiFlyout hideCloseButton onClose={onClose} ownFocus>
        <EuiFlyoutHeader hasBorder>
          {renderFormName()}
        </EuiFlyoutHeader>
        <EuiFlyoutBody>
          <EuiFormRow
            helpText={action == 'create' ? `You can't change this later.` : `This can't be changed.`}
            label='Rating scale for judgements'
          >
            {renderFormRatingScale()}
          </EuiFormRow>
          <EuiSpacer />
          <EuiFormRow
            helpText={<>A comma-separated list of <EuiLink href='https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-multiple-data-streams-indices' target='_blank'>index patterns</EuiLink> to scope searches.</>}
            label='Index pattern'
          >
            {renderFormIndexPattern()}
          </EuiFormRow>
          <EuiSpacer />
          <EuiFormRow
            helpText='Named variables for scenarios and strategies.'
            label='Params'
          >
            {renderFormParams()}
          </EuiFormRow>
        </EuiFlyoutBody>
        <EuiFlyoutFooter>
          <EuiFlexGroup justifyContent='spaceBetween'>
            <EuiFlexItem grow={false}>
              <EuiButtonEmpty
                disabled={isProcessing}
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
                disabled={isProcessing || isInvalidForm()}
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
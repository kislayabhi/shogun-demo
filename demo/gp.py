from django.http import HttpResponse,Http404
from django.template import RequestContext
from django.shortcuts import render_to_response
from common.kernel import get_kernel

import modshogun as sg
import numpy as np
import numpy.random as rnd
import h5py
import json

def entrance(request):
    arguments = [
        {
            'argument_type': 'select',
            'argument_name': 'kernel',
            'argument_items': ['GaussianKernel', 'PolynomialKernel', 'LinearKernel'],
            'argument_default': 'GaussianKernel'
        },
        {
            'argument_type': 'integer',
            'argument_name': 'degree',
            'argument_default': '5'
        },
        {
            'argument_type': 'decimal',
            'argument_label': 'Kernel Width',
            'argument_name': 'sigma',
            'argument_default': '2.0'},
        {
            'argument_type': 'button-group',
            'argument_items': [{'button_name': 'TrainGP'},
                               {'button_name': 'Clear'}]
        }
    ]
    properties = { 'title': 'Gaussian Process Regression Demo',
                   'template': {'type': 'coordinate-2dims',
                                'coordinate_system': {'horizontal_axis': {'range': [-5, 5]},
                                                      'vertical_axis': {'range': [-5, 5]}}},
                   'panels': [
                       {
                           'panel_name': 'arguments',
                           'panel_label': 'Arguments',
                           'panel_property': arguments
                       },
                       {
                           'panel_name': 'toy_data_generator',
                           'panel_label': 'Toy Data'
                       }]}
    return render_to_response("gp/index.html", properties, context_instance = RequestContext(request))

def train(request):
    result = []
    try:
        arguments = _read_toy_data(request)
        result = _process(*arguments)
    except:
        raise ValueError("Argument Error")

    return HttpResponse(json.dumps(result))

def _read_toy_data(request):
    y_set = []
    x_set = []
    toy_data = json.loads(request.POST['mouse_left_click_point_set'])
    for pt in toy_data:
        y_set.append(float(pt["y"]))
        x_set.append(float(pt["x"]))
    noise_level = float(request.POST['noise_level'])
    
    labels = np.array(y_set, dtype = np.float64)
    num = len(x_set)
    if num == 0:
        raise Http404
    examples = np.zeros((1, num))
    for i in xrange(num):
        examples[0,i] = x_set[i]
    feat_train = sg.RealFeatures(examples)
    labels = sg.RegressionLabels(labels)
    kernel = get_kernel(request, feat_train)
    return (feat_train, labels, noise_level, kernel)

def _process(feat_train, labels, noise_level, kernel):
    n_dimensions = 1

    likelihood = sg.GaussianLikelihood()
    likelihood.set_sigma(noise_level)
    covar_parms = np.log([2])
    hyperparams = {'covar': covar_parms, 'lik': np.log([1])}

    # construct covariance function
    SECF = kernel
    covar = SECF
    zmean = sg.ZeroMean()
    inf = sg.ExactInferenceMethod(SECF, feat_train, zmean, labels, likelihood)

    # location of unispaced predictions
    x_test = np.array([np.linspace(-5, 5, feat_train.get_num_vectors())])
    feat_test = sg.RealFeatures(x_test)

    gp = sg.GaussianProcessRegression(inf)
    gp.train()
    
#    gp.set_return_type(sg.GaussianProcessRegression.GP_RETURN_COV)
    covariance = gp.get_variance_vector(feat_test)
#    gp.set_return_type(sg.GaussianProcessRegression.GP_RETURN_MEANS)
    predictions = gp.get_mean_vector(feat_test)

    result = []
    for i in xrange(len(feat_test.get_feature_matrix()[0])):
        result.append({'x': feat_test.get_feature_matrix()[0][i],
                       'y': predictions[i],
                       'range_upper': predictions[i]+2*np.sqrt(covariance[i]),
                       'range_lower': predictions[i]-2*np.sqrt(covariance[i])})
    return result

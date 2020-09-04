"""
Standard markdown expander class to expand Brian objects to
markdown text using standard dictionary representation of baseexport
"""
from brian2.equations.equations import str_to_sympy
from brian2 import Quantity
from sympy import Derivative, symbols
from sympy.printing import latex
from sympy.abc import *
from markdown_strings import *
import numpy as np
import re

# define variables for often used delimiters
endll = '\n\n'
endl = '\n'
tab = '\t'


class Std_mdexpander():

    """
    Build Markdown texts from run dictionary.
    The class contain various expand functions for corresponding Brian
    objects and get standard dictionary as argument to expand them with
    sentences in markdown format.

    Note
    ----
    If suppose the user would like to change the format or wordings in
    the exported model descriptions, one can derive from this standard
    markdown expander class to override the required changes in expand
    functions.
    """

    def check_plural(self, iterable, singular_word=None,
                     allow_constants=True):
        """
        Function to attach plural form of the word
        by examining the following iterable

        Parameters
        ----------
        iterable : object with `__iter__` attribute
            Object that has to be examined

        singular_word : str, optional
            Word whose plural form has to searched in `singular_plural_dict`

        allow_constants : bool, optional
            Whether to assume non iterable as singular, if set as `True`,
            the `iterable` argument must be an iterable
        """
        count = 0
        # dict where adding 's' at the end won't work
        singular_plural_dict = {'index': 'indices',
                                'property': 'properties'
                            }
        # check iterable
        if hasattr(iterable, '__iter__'):
            for _ in iterable:
                count += 1
                if count > 1:
                    if singular_word:
                        try:
                            return singular_plural_dict[singular_word]
                        except KeyError:
                            raise Exception("The singular word is not found \
                                             in singular-plural dictionary.")
                    return 's'
        # check allow constants
        elif not allow_constants:
            raise IndexError("Suppose to be iterable object \
                            but instance got {}".format(type(iterable)))
        return ''

    def prepare_math_statements(self, statements, differential=False,
                                separate=False, equals='&#8592;'):
        """
        Prepare statements to render in markdown format

        Parameters
        ----------
        statements : str
            String containing mathematical equations and statements

        differential : bool, optional
            Whether should be treated as variable in differential equation

        separate : bool, optional
            Whether lhs and rhs of the statement should be separated and
            rendered
        
        equals : str, optional
            Equals operator, by default arrow from right to left
        """

        rend_str = ''
        # split multilines
        list_eqns = re.split(';|\n', statements)
        # loop through each line
        for statement in list_eqns:
            # check lhs-rhs to be separated
            if separate:
                # possible operators
                if ('+=' in statement or '=' in statement or
                    '-=' in statement):
                    # join lhs and rhs
                    lhs, rhs = re.split('-=|\+=|=', statement)
                    if '+=' in statement:
                        rend_str += (self.render_expression(lhs) +
                                     '+=' +self.render_expression(rhs))
                    elif '-=' in statement:
                        rend_str += (self.render_expression(lhs) +
                                     '-=' +self.render_expression(rhs))
                    else:
                        rend_str += (self.render_expression(lhs) +
                                     equals +  self.render_expression(rhs))
            # if need not separate
            else:
                rend_str += self.render_expression(statement, differential)
            rend_str += ', '
        # to remove ',' from last item
        return rend_str[:-2]

    def render_expression(self, expression, differential=False):
        """
        Function to render mathematical expression using
        `sympy.printing.latex`

        Parameters
        ----------

        expression : str, Quantity
            Expression that has to rendered

        differential : bool, optional
            Whether should be treated as variable in differential equation
        
        Returns
        -------

        rend_exp : str
            Markdown text for the expression
        """
        # change to str
        if isinstance(expression, Quantity):
            expression = str(expression)
        else:
            if not isinstance(expression, str):
                expression = str(expression)
            # convert to sympy expression
            expression = str_to_sympy(expression)
        # check to be treated as differential variable
        if differential:
            # independent variable is always 't'
            t = symbols('t')
            expression = Derivative(expression, 't')
        # render expression
        rend_exp = latex(expression, mode='equation',
                         itex=True, mul_symbol='.')
        # horrible way to remove _placeholder_{arg} inside brackets
        rend_exp = rend_exp.replace('_placeholder_{arg}', '-')
        rend_exp = rend_exp.replace('\operatorname', '')
        # check GitHub based markdown rendering
        if self.github_md:
            # to remove `$$`
            rend_exp = rend_exp[2:][:-2]
            # link to render as image
            git_rend_exp = (
            '<img src="https://render.githubusercontent.com/render/math?math=' +
            rend_exp + '">'
                        )
            return git_rend_exp
        # to remove `$` (in most md compiler single $ is used)
        return rend_exp[1:][:-1]

    def create_md_string(self, net_dict, brian_verbose=False, github_md=False):
        """
        Create markdown text by checking the standard dictionary and call
        required expand functions and arrange the descriptions
        """
        # get details about network runs
        overall_string = header('Network details', 1) + endl
        n_runs = 's'
        if len(net_dict) > 1:
            n_runs = ''
        # check github based math rendering
        self.github_md = github_md
        # start header to mention about no. of total run simulations
        overall_string += ('The Network consist' + n_runs + ' of {} \
                           simulation run'.format(
                                                bold(len(net_dict))
                                                ) +
                           self.check_plural(net_dict) +
                           endl + horizontal_rule() + endl)
        # start going to the dictionary items in particular run instance
        for run_indx in range(len(net_dict)):
            # details about the particular run
            run_dict = net_dict[run_indx]
            # start run header to say about duration
            if len(net_dict) > 1:
                run_string = (header('Run ' + str(run_indx + 1) +
                              ' details', 3) +
                              endl)
            else:
                run_string = endl
            run_string += ('Duration of simulation is ' +
                            bold(str(run_dict['duration'])) + endll)
            # map expand functions for particular components
            # h: normal 
            func_map = {'neurongroup': {'f': self.expand_NeuronGroup,
                                        'hb': 'NeuronGroup',
                                        'h': 'Neuron group'},
                       'poissongroup': {'f': self.expand_PoissonGroup,
                                        'hb': 'PoissonGroup',
                                        'h': 'Poisson spike source'},
                       'spikegeneratorgroup':
                                    {'f': self.expand_SpikeGeneratorGroup,
                                     'hb': 'SpikeGeneratorGroup',
                                     'h': 'Spike generating source'},
                       'statemonitor': {'f': self.expand_StateMonitor,
                                        'hb': 'StateMonitor',
                                        'h': 'Activity recorder'},
                       'spikemonitor': {'f': self.expand_SpikeMonitor,
                                        'hb': 'SpikeMonitor',
                                        'h': 'Spiking activity recorder'},
                       'eventmonitor': {'f': self.expand_EventMonitor,
                                        'hb': 'EventMonitor',
                                        'h': 'Event activity recorder'},
                       'populationratemonitor':
                                    {'f': self.expand_PopulationRateMonitor,
                                     'hb': 'PopulationRateMonitor',
                                     'h': 'Population rate recorder'},
                       'synapses': {'f': self.expand_Synapses,
                                    'hb': 'Synapse',
                                    'h': 'Synapse'},
                       'poissoninput': {'f': self.expand_PoissonInput,
                                         'hb': 'PoissonInput',
                                         'h': 'Poisson input'}}
            # loop through the components
            for (obj_key, obj_list) in run_dict['components'].items():
                # check the object component is in map
                if obj_key in func_map.keys():
                    # loop through the members in list
                    # check Brian based verbose is required
                    if brian_verbose:
                        obj_h = func_map[obj_key]['hb']
                    else:
                        obj_h = func_map[obj_key]['h']
                    run_string += (bold(obj_h +
                                   self.check_plural(obj_list) + ' defined:') +
                                   endl)
                    # point out components
                    for obj_mem in obj_list:
                        run_string += '- ' + func_map[obj_key]['f'](obj_mem)
                run_string += endl
            # differentiate connectors and initializers from
            # `initializers_connectors`
            initializer = []
            connector = []
            # check if they are available, if so expand them
            if 'initializers_connectors' in run_dict:
                # loop through the members in list
                for init_cont in run_dict['initializers_connectors']:
                    if init_cont['type'] is 'initializer':
                        initializer.append(init_cont)
                    else:
                        connector.append(init_cont)
            if initializer:
                if brian_verbose:
                    run_string += bold('Initializer' +
                                    self.check_plural(initializer) +
                                    ' defined:') + endl
                else:
                    run_string += bold('Initializing values at \
                                        starting:') + endl
                # loop through the initializers
                for initit in initializer:
                    run_string += '- ' + self.expand_initializer(initit)
            if connector:
                run_string += endl
                run_string += bold('Synaptic Connection' +
                                   self.check_plural(connector) +
                                   ' defined:') + endl
                # loop through the connectors
                for connect in connector:
                    run_string += '- ' + self.expand_connector(connect)
            # check inactive objects
            if 'inactive' in run_dict:
                run_string += endl
                run_string += (bold('Inactive member' + 
                               self.check_plural(run_dict['inactive']) + ':')
                               + endl)
                run_string += ', '.join(run_dict['inactive'])
            overall_string += run_string
        # final markdown text to pass to `build()`
        self.md_text = overall_string

        return self.md_text

    def expand_NeuronGroup(self, neurongrp):
        """
        Expand NeuronGroup from standard dictionary

        Parameters
        ----------

        neurongrp : dict
            Standard dictionary of NeuronGroup
        """
        # start expanding
        md_str = ''
        # name and size
        md_str += 'Name ' + bold(neurongrp['name']) + ', with \
                population size ' + bold(neurongrp['N']) + '.' + endll
        # expand model equations
        md_str += tab + bold('Dynamics:') + endll
        md_str += self.expand_equations(neurongrp['equations'])
        if neurongrp['user_method']:
            md_str += (tab + neurongrp['user_method'] +
                    ' method is used for integration' + endll)
        # expand associated events
        if 'events' in neurongrp:
            md_str += tab + bold('Events:') + endll
            md_str += self.expand_events(neurongrp['events'])
        # expand identifiers associated
        if 'identifiers' in neurongrp:
            md_str += tab + bold('Constants:') + endll
            md_str += self.expand_identifiers(neurongrp['identifiers'])
        # expand run_regularly()
        if 'run_regularly' in neurongrp:
            md_str += (tab + bold('Run regularly') + 
            self.check_plural(neurongrp['run_regularly']) + ': ' + endll)
            for run_reg in neurongrp['run_regularly']:
                md_str += self.expand_runregularly(run_reg)

        return md_str

    def expand_identifier(self, ident_key, ident_value):
        """
        Expand identifer (key-value form)
        
        Parameters
        ----------
        
        ident_key : str
            Identifier name
        ident_value : Quantity, str, dict
            Identifier value. Dictionary if identifer is of type either
            `TimedArray` or custom function
        """
        ident_str = ''
        # if not `TimedArray` nor custom function
        if type(ident_value) != dict:
            ident_str += (self.render_expression(ident_key) + ": " +
                        self.render_expression(ident_value))
        # expand dictionary
        else:
            ident_str += (self.render_expression(ident_key) + ' of type ' +
                            ident_value['type'])
            if ident_value['type'] is 'timedarray':
                ident_str += (' with dimension ' +
                              self.render_expression(ident_value['ndim']) +
                              ' and dt as ' +
                              self.render_expression(ident_value['dt']))
        return ident_str + ', '

    def expand_identifiers(self, identifiers):
        """
        Expand function to loop through identifiers and call
        `expand_identifier`
        """
        idents_str = ''
        # loop through all identifiers
        for key, value in identifiers.items():
            idents_str += self.expand_identifier(key, value)
        # to remove ', ' for last item
        idents_str = tab + idents_str[:-2] + endll
        return idents_str

    def expand_event(self, event_name, event_details):
        """
        Function to expand event dictionary

        Parameters
        ----------

        event_name : str
            name of the event
        
        event_details : dict
            details of the event
        """
        event_str = ''
        event_str += tab + 'Event ' + bold(event_name) + ', '
        event_str += ('after ' +
                    self.render_expression(event_details['threshold']['code']))
        if 'reset' in event_details:
            event_str += (', ' + 
                        self.prepare_math_statements(
                                        event_details['reset']['code'],
                                        separate=True)
                         )
        if 'refractory' in event_details:
            event_str += ', with refractory ' 
            event_str += self.render_expression(event_details['refractory'])

        return event_str + endll

    def expand_events(self, events):
        """
        Expand function to loop through all events and call
        `expand_event`
        """
        events_str = ''
        for name, details in events.items():
            events_str += self.expand_event(name, details)

        return events_str

    def expand_equation(self, var, equation):
        """
        Expand Equation from equation dictionary

        Parameters
        ----------

        var : str
            Variable name
        equation : dict
            Details of the equation
        """
        rend_eqn = ''   
        if equation['type'] == 'differential equation':
            rend_eqn +=  self.render_expression(var, differential=True)
        elif equation['type'] == 'subexpression':
            rend_eqn +=  self.render_expression(var)
        else:
            rend_eqn += 'Parameter ' + self.render_expression(var)
        if 'expr' in equation:
            rend_eqn +=  '=' + self.render_expression(equation['expr'])
        rend_eqn += (", where unit of " + self.render_expression(var) +
                        " is " + str(equation['unit']))
        if 'flags' in equation:
            rend_eqn += (' and ' +
                         ', '.join(str(f) for f in equation['flags']) +
                         ' as flag' + self.check_plural(equation['flags']) +
                         ' associated')
        return tab + rend_eqn + endll

    def expand_equations(self, equations):
        """
        Function to loop all equations
        """
        rend_eqns = ''
        for (var, equation) in equations.items():
            rend_eqns += self.expand_equation(var, equation)
        return rend_eqns

    def expand_initializer(self, initializer):
        """
        Expand initializer from initializer dictionary

        Parameters
        ----------

        initializer : dict
            Dictionary representation of initializer
        """
        init_str = ''
        init_str += ('Variable ' +
                     self.render_expression(initializer['variable']) +
                     ' of ' +  initializer['source'] + ' initialized with ' +
                     self.render_expression(initializer['value'])
                    )
        # not a good checking
        if (isinstance(initializer['index'], str) and 
        (initializer['index'] != 'True' and initializer['index'] != 'False')):
            init_str += ' on condition ' + initializer['index']
        elif (isinstance(initializer['index'], bool) or
            (initializer['index'] == 'True' or
             initializer['index'] == 'False')):
            if initializer['index'] or initializer['index'] == 'True':
                init_str += ' to all members'
            else:
                init_str += ' to no member'
        else:
            init_str += (' to member' +
                         self.check_plural(initializer['index']) + ' ')
            if not hasattr(initializer['index'], '__iter___'):
                init_str += str(initializer['index'])
            else:
                init_str += ','.join(
                    [str(ind) for ind in initializer['index']]
                                    )
        if 'identifiers' in initializer:
            init_str += ('. Identifier' +
                        self.check_plural(initializer['identifiers']) +
                        ' associated: ' +
                        self.expand_identifiers(initializer['identifiers']))
        return init_str + endll

    def expand_connector(self, connector):
        """
        Expand connector from connector dictionary

        Parameters
        ----------

        connector : dict
            Dictionary representation of connector
        """
        con_str = ''
        con_str += ('Connection from ' + connector['source'] +
                    ' to ' + connector['target'])
        if 'i' in connector:
            con_str += ('. From source group ' +
                        self.check_plural(connector['i'], 'index') + ': ')
            if not isinstance(connector['i'], str):
                if hasattr(connector['i'], '__iter__'):
                    con_str += ', '.join(str(ind) for ind in connector['i'])
                else:
                    con_str += str(connector['i'])
            else:
                con_str += ' with generator syntax ' + connector['i']
            if 'j' in connector:
                con_str += (' to target group ' +
                            self.check_plural(connector['j'], 'index') + ': ')
                if not isinstance(connector['j'], str):
                    if hasattr(connector['j'], '__iter__'):
                        con_str += ', '.join(
                                        str(ind) for ind in connector['j']
                                            )
                    else:
                        con_str += str(connector['j'])
                else:
                    con_str += ' with generator syntax ' + connector['j']
            else:
                con_str += ' to all target group members'

        elif 'j' in connector:
            con_str += '. Connection for all members in source group'
            if not isinstance(connector['j'], str):
                con_str += (' to target group ' +
                        self.check_plural(connector['j'], 'index') + ': ')
                if hasattr(connector['j'], '__iter__'):
                    con_str += ', '.join(
                                    str(ind) for ind in connector['j']
                                        )
                else:
                    con_str += str(connector['j'])
            else: 
                con_str += (' to target group with generator syntax ' +
                            connector['j'])

        elif 'condition' in connector:
            con_str += (' with condition ' +
                        self.render_expression(connector['condition']))
        if connector['probability'] != 1:
            con_str += (', with probability ' +
                        self.render_expression(connector['probability']))
        if connector['n_connections'] != 1:
            con_str += (', with number of connections ' +
                        self.render_expression(connector['n_connections']))
        if 'identifiers' in connector:
            con_str += ('. Constants associated: ' +
                        self.expand_identifiers(connector['identifiers']))
        return con_str + endll

    def expand_PoissonGroup(self, poisngrp):
        """
        Expand PoissonGroup from standard dictionary

        Parameters
        ----------

        poisngrp : dict
            Standard dictionary of PoissonGroup
        """

        md_str = ''
        md_str += (tab + 'Name ' + bold(poisngrp['name']) + ', with \
                population size ' + bold(poisngrp['N']) +
                ' and rate as ' + self.render_expression(poisngrp['rates']) +
                '.' + endll)
        if 'identifiers' in poisngrp:
            md_str += tab + bold('Constants:') + endll
            md_str += self.expand_identifiers(poisngrp['identifiers'])
        if 'run_regularly' in poisngrp:
            md_str += tab + bold('Run regularly: ') + endll
            for run_reg in poisngrp['run_regularly']:
                md_str += self.expand_runregularly(run_reg)

        return md_str

    def expand_SpikeGeneratorGroup(self, spkgen):
        """
        Expand SpikeGeneratorGroup from standard dictionary

        Parameters
        ----------

        spkgen : dict
            Standard dictionary of SpikeGeneratorGroup
        """
        md_str = ''
        md_str += (tab + 'Name ' + bold(spkgen['name']) +
                ', with population size ' + bold(spkgen['N']) +
                ', has neuron' + self.check_plural(spkgen['indices']) + ': ' +
                ', '.join(str(i) for i in spkgen['indices']) +
                ' that spike at times ' +
                ', '.join(str(t) for t in spkgen['times']) +
                ', with period ' + str(spkgen['period']) +
                '.' + endll)
        if 'run_regularly' in spkgen:
            md_str += tab + bold('Run regularly: ') + endll
            for run_reg in spkgen['run_regularly']:
                md_str += self.expand_runregularly(run_reg)

        return md_str

    def expand_StateMonitor(self, statemon):
        """
        Expand StateMonitor from standard dictionary

        Parameters
        ----------

        statemon : dict
            Standard dictionary of StateMonitor
        """
        md_str = ''
        md_str += (tab + 'Monitors variable' + 
                   self.check_plural(statemon['variables']) + ': ' +
                   ','.join(
                    [self.render_expression(var) for var in statemon['variables']]
                           ) +
                   ' of ' + statemon['source'])
        if isinstance(statemon['record'], bool):
            if statemon['record']:
                md_str += ' for all members'
        else:
            # another bad hack (before with initializers)
            if not statemon['record'].size:
                md_str += ' for no member'
            else:
                md_str += (', for member' + self.check_plural(statemon['record']) +
                        ': ' +
                        ','.join([str(ind) for ind in statemon['record']]) +
                        '.' + endll)
        return md_str

    def expand_SpikeMonitor(self, spikemon):
        """
        Expand SpikeMonitor from standard representation

        Parameters
        ----------

        spikemon : dict
            Standard dictionary of SpikeMonitor
        """
        return self.expand_EventMonitor(spikemon)

    def expand_EventMonitor(self, eventmon):
        """
        Expand EventMonitor from standard representation

        Parameters
        ----------

        eventmon : dict
            Standard dictionary of EventMonitor
        """
        md_str = ''
        md_str += (tab + 'Monitors variable' +
                self.check_plural(eventmon['variables']) + ': ' +
                ','.join(
                    [self.render_expression(var) for var in eventmon['variables']]
                    ) +
                ' of ' + eventmon['source'])
        if isinstance(eventmon['record'], bool):
            if eventmon['record']:
                md_str += ' for all members'
        else:
            if not eventmon['record'].size:
                md_str += ' for no member'
            else:
                md_str += (', for member' + self.check_plural(eventmon['record']) +
                        ': ' +
                        ','.join([str(ind) for ind in eventmon['record']]))
        md_str += (' when event ' + bold(eventmon['event']) +
                    ' is triggered.' + endll)
        return md_str

    def expand_PopulationRateMonitor(self, popratemon):
        """
        Expand PopulationRateMonitor

        Parameters
        ----------

        popratemon : dict
            PopulationRateMonitor's baseexport dictionary
        """
        md_str = ''
        md_str += (tab + 'Monitors the population of ' + popratemon['source'] +
                '.' + endll)
        return md_str

    def expand_pathway(self, pathway):
        """
        Expand `SynapticPathway`
        
        Parameters
        ----------

        pathway : dict
            SynapticPathway's baseexport dictionary
        """
        md_str = (tab + 'On ' + bold(pathway['prepost']) +
                ' of event ' + pathway['event'] + ' statements: ' +
                self.prepare_math_statements(pathway['code'], separate=True) +
                ' executed'
                )
        # check delay is associated
        if 'delay' in pathway:
            md_str += (', with synaptic delay of ' +
                    self.render_expression(pathway['delay']))

        return md_str + endll

    def expand_pathways(self, pathways):
        """
        Loop through pathways and call `expand_pathway`
        """
        path_str = ''
        for pathway in pathways:
            path_str += self.expand_pathway(pathway)
        return path_str

    def expand_summed_variable(self, sum_variable):
        """
        Expand Summed variable
        
        Parameters
        ----------

        sum_variabe : dict
            SummedVariable's baseexport dictionary
        """
        md_str = (tab + 'Updates target group ' + sum_variable['target'] +
                  ' with statement: ' +
                  self.render_expression(sum_variable['code']) +
                  endll)

        return md_str

    def expand_summed_variables(self, sum_variables):
        """
        Loop through summed variables and call `expand_summed_variable`
        """
        sum_var_str = ''
        for sum_var in sum_variables:
            sum_var_str += self.expand_summed_variable(sum_var)
        return sum_var_str

    def expand_Synapses(self, synapse):
        """
        Expand `Synapses` details from Baseexporter dictionary

        Parameters
        ----------

        synapse : dict
            Dictionary representation of `Synapses` object
        """
        md_str = ''
        md_str += (tab + 'From ' + synapse['source'] +
                ' to ' + synapse['target'] + endll
                )
        # expand model equations
        if 'equations' in synapse:
            md_str += tab + bold('Dynamics:') + endll
            md_str += tab + self.expand_equations(synapse['equations'])
            if 'user_method' in synapse:
                md_str += (tab + synapse['user_method'] + 
                    ' method is used for integration' + endll)
        # expand pathways using `expand_pathways`
        if 'pathways' in synapse:
            md_str += tab + bold('Pathways:') + endll
            md_str += self.expand_pathways(synapse['pathways'])
        # expand summed_variables using `expand_summed_variables`
        if 'summed_variables' in synapse:
            md_str += tab + bold('Summed variables: ') + endll
            md_str += self.expand_summed_variables(synapse['summed_variables'])
        # expand identifiers if defined
        if 'identifiers' in synapse:
            md_str += tab + bold('Constants:') + endll
            md_str += self.expand_identifiers(synapse['identifiers'])
        return md_str

    def expand_PoissonInput(self, poinp):
        """
        Expand PoissonInput

        Parameters
        ----------

        poinp : dict
            Standard dictionary representation for PoissonInput
        """
        md_str = ''
        md_str += (tab + 'PoissonInput with size ' + bold(poinp['N']) +
                ' gives input to variable ' +
                self.render_expression(poinp['target_var']) +
                ' with rate ' + self.render_expression(poinp['rate']) +
                ' and weight of ' + self.render_expression(poinp['weight']) +
                endll)
        if 'identifiers' in poinp:
            md_str += tab + bold('Constants:') + endll
            md_str += self.expand_identifiers(poinp['identifiers'])
        return md_str

    def expand_runregularly(self, run_reg):
        """
        Expand run_regularly from standard dictionary

        Parameters
        ----------

        run_reg : dict
            Standard dictionary representation for run_regularly()
        """
        md_str = (tab + 'For every ' + self.render_expression(run_reg['dt']) +
                ' code: ' +
                    self.prepare_math_statements(run_reg['code'], separate=True) +
                    ' will be executed' + endll)
        return md_str

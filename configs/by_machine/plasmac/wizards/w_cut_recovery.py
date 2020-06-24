#!/usr/bin/env python

'''
w_cut_recovery.py

Copyright (C) 2019 2020 Phillip A Carter

This program is free software; you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''

import os
import gtk
import hal
import linuxcnc
import gobject
import time

class recovery:

    def __init__(self):
        self.ini = True
        inFile = '~/linuxcnc_print.txt'
        with open('{}/linuxcnc_print.txt'.format(os.path.expanduser('~')), 'r') as f_in:
            for line in f_in:
                if line.startswith('INIFILE='):
                    iniFile = line.split('=')[1].strip()
                    break
        try:
            self.i = linuxcnc.ini(iniFile)
        except:
            print('Could not find ini file')
            self.ini = False
        try:
            self.h = hal.component('dummy')
            self.h.ready()
        except:
            pass
        if not hal.get_value('halui.program.is-paused'):
            print('Cannot load cut recovery because program is not paused')
            self.ini = False
        if self.ini:
            self.W = gtk.Window()
            self.W.set_title('PlasmaC Cut Recovery')
            self.W.set_position(gtk.WIN_POS_MOUSE)
            self.W.set_keep_above(True)
            self.W.connect('delete_event', self.on_window_delete_event)
            self.create_widgets()
            self.W.show_all()
            self.s = linuxcnc.stat()
            self.c = linuxcnc.command()
            self.clear_offsets()
            self.xOrig = hal.get_value('axis.x.eoffset-counts')
            self.yOrig = hal.get_value('axis.y.eoffset-counts')
            self.zOrig = hal.get_value('axis.z.eoffset-counts')
            self.oScale = hal.get_value('plasmac.offset-scale')
            self.xMin = float(self.i.find('AXIS_X', 'MIN_LIMIT'))
            self.xMax = float(self.i.find('AXIS_X', 'MAX_LIMIT'))
            self.yMin = float(self.i.find('AXIS_Y', 'MIN_LIMIT'))
            self.yMax = float(self.i.find('AXIS_Y', 'MAX_LIMIT'))
            self.zMin = float(self.i.find('AXIS_Z', 'MIN_LIMIT'))
            self.zMax = float(self.i.find('AXIS_Z', 'MAX_LIMIT'))
            gobject.timeout_add(100, self.periodic)
        else:
            raise SystemExit()

    def periodic(self):
        if hal.get_value('plasmac.cut-recovery') and \
          (hal.get_value('plasmac.state-out') == 1 or \
           hal.get_value('plasmac.state-out') == 24):
            self.clear_offsets()
            raise SystemExit()
        if hal.get_value('plasmac.x-offset') or hal.get_value('plasmac.y-offset'):
            self.feed_disable()
        else:
            self.feed_enable()
        return True

    def dialog_error(self, error):
        md = gtk.MessageDialog(self.W, 
                               gtk.DIALOG_DESTROY_WITH_PARENT,
                               gtk.MESSAGE_ERROR, 
                               gtk.BUTTONS_CLOSE,
                               error)
        md.run()
        md.destroy()

    def rev_pressed(self, widget):
        self.paused_motion(-1)

    def rev_released(self, widget):
        self.paused_motion(0)

    def fwd_pressed(self, widget):
        self.paused_motion(1)

    def fwd_released(self, widget):
        self.paused_motion(0)

    def paused_motion(self, direction):
        speed = float(self.rate.get_value()) * 0.01 * direction
        hal.set_p('plasmac.paused-motion-speed',str(speed))

    def xPlus_pressed(self, widget):
        if hal.get_value('plasmac.axis-x-position') + \
           hal.get_value('axis.x.eoffset-counts') * self.oScale + \
           hal.get_value('plasmac_run.kerf-width-f') > self.xMax:
            msg = 'X axis motion would trip X maximum limit'
            self.dialog_error(msg)
            return
        move = int(hal.get_value('plasmac_run.kerf-width-f') / self.oScale * 1)
        hal.set_p('plasmac.x-offset', '{}'.format(str(hal.get_value('axis.x.eoffset-counts') + move)))
        hal.set_p('plasmac.cut-recovery', '1')

    def xMinus_pressed(self, widget):
        if hal.get_value('plasmac.axis-x-position') + \
           hal.get_value('axis.x.eoffset-counts') * self.oScale - \
           hal.get_value('plasmac_run.kerf-width-f') < self.xMin:
            msg = 'X axis motion would trip X mimimum limit'
            self.dialog_error(msg)
            return
        move = int(hal.get_value('plasmac_run.kerf-width-f') / self.oScale * -1)
        hal.set_p('plasmac.x-offset', '{}'.format(str(hal.get_value('axis.x.eoffset-counts') + move)))
        hal.set_p('plasmac.cut-recovery', '1')

    def yPlus_pressed(self, widget):
        if hal.get_value('plasmac.axis-y-position') + \
           hal.get_value('axis.y.eoffset-counts') * self.oScale + \
           hal.get_value('plasmac_run.kerf-width-f') > self.yMax:
            msg = 'Y axis motion would trip Y maximum limit'
            self.dialog_error(msg)
            return
        move = int(hal.get_value('plasmac_run.kerf-width-f') / self.oScale * 1)
        hal.set_p('plasmac.y-offset', '{}'.format(str(hal.get_value('axis.y.eoffset-counts') + move)))
        hal.set_p('plasmac.cut-recovery', '1')

    def yMinus_pressed(self, widget):
        if hal.get_value('plasmac.axis-y-position') + \
           hal.get_value('axis.y.eoffset-counts') * self.oScale - \
           hal.get_value('plasmac_run.kerf-width-f') < self.yMin:
            msg = 'Y axis motion would trip Y minimum limit'
            self.dialog_error(msg)
            return
        move = int(hal.get_value('plasmac_run.kerf-width-f') / self.oScale * -1)
        hal.set_p('plasmac.y-offset', '{}'.format(str(hal.get_value('axis.y.eoffset-counts') + move)))
        hal.set_p('plasmac.cut-recovery', '1')

    def zPlus_pressed(self, widget):
        msg = 'Z axis motion not enable yet'
        self.dialog_error(msg)

    def zMinus_pressed(self, widget):
        msg = 'Z axis motion not enable yet'
        self.dialog_error(msg)

    def resume_pressed(self, widget):
        self.s.poll()
        if not self.s.paused:
            return
        if self.s.task_mode != linuxcnc.MODE_AUTO:
            msg = 'LinuxCNC is not in auto mode'
            self.dialog_error(msg)
            self.clear_offsets()
            raise SystemExit()
        self.c.auto(linuxcnc.AUTO_RESUME)
        self.clear_offsets()
        raise SystemExit()

    def cancel_pressed(self, widget):
        self.clear_offsets()
        raise SystemExit()

    def on_window_delete_event(self,window,event):
        self.clear_offsets()
        raise SystemExit()

    def clear_offsets(self):
        hal.set_p('plasmac.x-offset', '0')
        hal.set_p('plasmac.y-offset', '0')

    def feed_enable(self):
        self.rev.set_sensitive(True)
        self.feed.set_sensitive(True)
        self.fwd.set_sensitive(True)

    def feed_disable(self):
        self.rev.set_sensitive(False)
        self.feed.set_sensitive(False)
        self.fwd.set_sensitive(False)

    def create_widgets(self):
        if not self.ini:
            return False
        self.T = gtk.Table()
        self.T.set_homogeneous(True)
        self.W.add(self.T)
        self.rev = gtk.Button('Rev')
        self.rev.connect('pressed', self.rev_pressed)
        self.rev.connect('released', self.rev_released)
        self.T.attach(self.rev, 0, 1, 0, 2)
        self.rate = gtk.Adjustment(value=50, lower=1, upper=100, step_incr=1, page_incr=10, page_size=0) 
        self.rate.emit('value_changed')
        self.feed = gtk.HScale(adjustment = self.rate)
        self.feed.set_digits(0)
        self.T.attach(self.feed, 1, 4, 0, 2)
        self.fwd = gtk.Button('Fwd')
        self.fwd.connect('pressed', self.fwd_pressed)
        self.fwd.connect('released', self.fwd_released)
        self.T.attach(self.fwd, 4, 5, 0, 2)
        self.yPlus = gtk.Button('Y+')
        self.yPlus.connect('pressed', self.yPlus_pressed)
        self.T.attach(self.yPlus, 2, 3, 3, 5)
        self.xMinus = gtk.Button('X-')
        self.xMinus.connect('pressed', self.xMinus_pressed)
        self.T.attach(self.xMinus, 1, 2, 5, 7)
        self.xPlus = gtk.Button('X+')
        self.xPlus.connect('pressed', self.xPlus_pressed)
        self.T.attach(self.xPlus, 3, 4, 5, 7)
        self.yMinus = gtk.Button('Y-')
        self.yMinus.connect('pressed', self.yMinus_pressed)
        self.T.attach(self.yMinus, 2, 3, 7, 9)
        self.resume = gtk.Button('Resume\nCut')
        for child in self.resume.children():
            child.set_justify(gtk.JUSTIFY_CENTER)
        self.resume.connect('pressed', self.resume_pressed)
        self.T.attach(self.resume, 0, 1, 10, 12)
        self.cancel = gtk.Button('Cancel')
        self.cancel.connect('pressed', self.cancel_pressed)
        self.T.attach(self.cancel, 4, 5, 10, 12)
        hal.set_p('plasmac_run.preview-tab', '1')

if __name__ == '__main__':
   try:
       a = recovery()
       gtk.main()
   except KeyboardInterrupt:
       pass

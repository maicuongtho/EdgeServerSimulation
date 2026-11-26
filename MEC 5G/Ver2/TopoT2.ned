//
// Hierarchical 5G MEC Topology (TopoT2: Local Edge vs. Regional/Central Edge)
// Author: Mai Cuong Tho (thomc@ntu.edu.vn)
// Framework: Simu5G / OMNeT++
//

package _5g_experiments.simulations.NafosMechostPolicyEval;

import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import inet.networklayer.ipv4.RoutingTableRecorder;
import inet.node.ethernet.Eth10G;
import simu5g.common.binder.Binder;
import simu5g.common.carrierAggregation.CarrierAggregation;
import simu5g.nodes.NrUe;
import simu5g.nodes.gNodeB;
import simu5g.nodes.Upf;
import simu5g.nodes.BackgroundCell;
import simu5g.nodes.MecHost;
import simu5g.mec.orchestrator.MecOrchestrator;
import simu5g.mec.ualcmp.Ualcmp;
import simu5g.world.radio.LteChannelControl;

network TopoT2
{
    parameters:
        int numUe = default(1);
        int numBgCells = default(0);

        // Configurable access link delays for Local Edge vs. Regional Edge
        double mecHost1LinkDelay @unit(s) = default(1ms);   // Local Edge 1 (at I-UPF 1)
        double mecHost2LinkDelay @unit(s) = default(1ms);   // Local Edge 2 (at I-UPF 2)
        double mecHost3LinkDelay @unit(s) = default(18ms);  // Regional/Central Edge (at Anchor UPF)

        @display("i=block/network2;bgb=1150,700;bgi=background/pisa");

    submodules:
        channelControl: LteChannelControl {
            @display("p=55,35;is=s");
        }

        routingRecorder: RoutingTableRecorder {
            @display("p=55,85;is=s");
        }

        configurator: Ipv4NetworkConfigurator {
            @display("p=55,135");
        }

        binder: Binder {
            @display("p=55,185;is=s");
        }

        carrierAggregation: CarrierAggregation {
            @display("p=55,250;is=s");
        }

        // Control & Management Plane (ETSI MEC)
        mecOrchestrator: MecOrchestrator {
            @display("p=250,75");
        }

        ualcmp: Ualcmp {
            @display("p=410,75");
        }

        // 5G Core Network (Anchor UPF & Intermediate UPFs)
        upf: Upf {
            @display("p=550,145");
        }

        iUpf1: Upf {
            @display("p=390,285");
        }

        iUpf2: Upf {
            @display("p=710,285");
        }

        // Regional / Central MEC Host (High CPU, Higher Link Delay)
        mecHost3: MecHost {
            @display("p=860,145");
        }

        // Local Edge MEC Hosts (Low CPU, Ultra-low Link Delay)
        mecHost1: MecHost {
            @display("p=210,285");
        }

        mecHost2: MecHost {
            @display("p=890,285");
        }

        // 5G NR Radio Access Network (gNodeBs)
        gnb1: gNodeB {
            @display("p=390,440;is=vl");
        }

        gnb2: gNodeB {
            @display("p=710,440;is=vl");
        }

        bgCell[numBgCells]: BackgroundCell {
            @display("p=210,590;is=vl");
        }

        // 5G User Equipment
        ue[numUe]: NrUe {
            @display("p=550,550");
        }

    connections:
        // 5G Core N9 Interfaces (Anchor UPF <-> I-UPFs)
        upf.pppg++ <--> Eth10G <--> iUpf1.pppg++;
        upf.pppg++ <--> Eth10G <--> iUpf2.pppg++;

        // 5G Core N3 Interfaces (I-UPFs <-> gNodeBs)
        iUpf1.pppg++ <--> Eth10G <--> gnb1.ppp;
        iUpf2.pppg++ <--> Eth10G <--> gnb2.ppp;

        // MEC Control & Lifecycle Management Plane
        ualcmp.ppp++ <--> Eth10G <--> upf.filterGate;
        ualcmp.toMecOrchestrator --> mecOrchestrator.fromUALCMP;
        ualcmp.fromMecOrchestrator <-- mecOrchestrator.toUALCMP;

        // Local Edge Data-Plane Access Links (via I-UPFs)
        mecHost1.ppp++ <--> Eth10G {
            delay = parent.mecHost1LinkDelay;
        } <--> iUpf1.pppg++;

        mecHost2.ppp++ <--> Eth10G {
            delay = parent.mecHost2LinkDelay;
        } <--> iUpf2.pppg++;

        // Regional/Central Edge Data-Plane Access Link (via Anchor UPF)
        mecHost3.ppp++ <--> Eth10G {
            delay = parent.mecHost3LinkDelay;
        } <--> upf.pppg++;

        // X2 / Xn Inter-gNB Interface
        gnb1.x2++ <--> Eth10G <--> gnb2.x2++;
}
